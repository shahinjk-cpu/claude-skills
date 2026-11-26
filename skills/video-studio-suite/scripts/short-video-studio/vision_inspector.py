#!/usr/bin/env python3
"""
[跨平台视觉原材感知引擎]
- macOS 优先编译（原子锁替换防并发损坏）并缓存原生 Apple Vision Swift CLI：
  使用 DispatchQueue.concurrentPerform 并行跑通人脸/五官关键点（修正像素纵横比畸变）、
  主体显著性热区与精确 OCR，任何异常显式打印 stderr 并返回非零。
- 非 macOS 或无 swiftc 环境优雅降级为 PIL (exif_transpose) + numpy 梯度显著性估算。
- 复用 common.bbox_iou，提供纯 numpy 拉普拉斯锐度方差计算。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPTS_ROOT = Path(__file__).resolve().parent
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common import bbox_iou, compute_bt709_luma, maybe_reexec_in_venv

if __name__ == "__main__":
    maybe_reexec_in_venv()

import numpy as np
from PIL import Image, ImageOps

VISION_INSPECTOR_SWIFT_SRC = r"""
import Foundation
import Vision
import ImageIO

func topLeftRect(_ b: CGRect) -> [String: Double] {
    return [
        "x": Double(b.origin.x),
        "y": Double(1.0 - b.origin.y - b.size.height),
        "w": Double(b.size.width),
        "h": Double(b.size.height)
    ]
}

func eyeMetrics(_ region: VNFaceLandmarkRegion2D?, faceBox b: CGRect, dispW: Double, dispH: Double) -> (cx: Double, cy: Double, openRatio: Double)? {
    guard let pts = region?.normalizedPoints, pts.count >= 2 else { return nil }
    var sumX = 0.0
    var sumY = 0.0
    var minX = 1.0, maxX = 0.0
    var minY = 1.0, maxY = 0.0
    for pt in pts {
        let gx = Double(b.origin.x) + Double(pt.x) * Double(b.size.width)
        let gy = 1.0 - (Double(b.origin.y) + Double(pt.y) * Double(b.size.height))
        sumX += gx
        sumY += gy
        minX = min(minX, Double(pt.x))
        maxX = max(maxX, Double(pt.x))
        minY = min(minY, Double(pt.y))
        maxY = max(maxY, Double(pt.y))
    }
    let wPx = max(1e-3, (maxX - minX) * Double(b.size.width) * max(1.0, dispW))
    let hPx = max(0.0, (maxY - minY) * Double(b.size.height) * max(1.0, dispH))
    let cnt = Double(pts.count)
    return (sumX / cnt, sumY / cnt, hPx / wPx)
}

func mouthOpenRatio(_ region: VNFaceLandmarkRegion2D?, faceBox b: CGRect, dispW: Double, dispH: Double) -> Double {
    guard let pts = region?.normalizedPoints, pts.count >= 4 else { return 0.0 }
    var minX = 1.0, maxX = 0.0
    var minY = 1.0, maxY = 0.0
    for pt in pts {
        minX = min(minX, Double(pt.x))
        maxX = max(maxX, Double(pt.x))
        minY = min(minY, Double(pt.y))
        maxY = max(maxY, Double(pt.y))
    }
    let wPx = max(1e-3, (maxX - minX) * Double(b.size.width) * max(1.0, dispW))
    let hPx = max(0.0, (maxY - minY) * Double(b.size.height) * max(1.0, dispH))
    return hPx / wPx
}

let args = Array(CommandLine.arguments.dropFirst())
if args.isEmpty { exit(1) }

var outputs = [String?](repeating: nil, count: args.count)
var errCount = 0
let lock = NSLock()

DispatchQueue.concurrentPerform(iterations: args.count) { idx in
    let path = args[idx]
    let url = URL(fileURLWithPath: path)
    guard let src = CGImageSourceCreateWithURL(url as CFURL, nil),
          let cgImg = CGImageSourceCreateImageAtIndex(src, 0, nil) else {
        let empty: [String: Any] = ["file": path, "width": 0, "height": 0, "faces": [], "saliency": NSNull(), "texts": [], "read_error": true]
        if let d = try? JSONSerialization.data(withJSONObject: empty),
           let s = String(data: d, encoding: .utf8) {
            lock.lock(); outputs[idx] = s; errCount += 1; lock.unlock()
        }
        return
    }

    var cgOrientation = CGImagePropertyOrientation.up
    if let props = CGImageSourceCopyPropertiesAtIndex(src, 0, nil) as? [CFString: Any],
       let rawOri = props[kCGImagePropertyOrientation] as? UInt32,
       let parsedOri = CGImagePropertyOrientation(rawValue: rawOri) {
        cgOrientation = parsedOri
    }
    let swapped = (cgOrientation == .left || cgOrientation == .right || cgOrientation == .leftMirrored || cgOrientation == .rightMirrored)
    let dispWidth = swapped ? cgImg.height : cgImg.width
    let dispHeight = swapped ? cgImg.width : cgImg.height

    let faceReq = VNDetectFaceLandmarksRequest()
    let ocrReq = VNRecognizeTextRequest()
    ocrReq.recognitionLevel = .accurate
    ocrReq.recognitionLanguages = ["zh-Hans", "en-US"]
    ocrReq.usesLanguageCorrection = true

    var requests: [VNRequest] = [faceReq, ocrReq]
    var salReq: VNGenerateAttentionBasedSaliencyImageRequest? = nil
    if #available(macOS 10.15, *) {
        let sr = VNGenerateAttentionBasedSaliencyImageRequest()
        salReq = sr
        requests.append(sr)
    }

    let handler = VNImageRequestHandler(cgImage: cgImg, orientation: cgOrientation, options: [:])
    do {
        try handler.perform(requests)
    } catch {
        let errItem: [String: Any] = ["file": path, "width": dispWidth, "height": dispHeight, "faces": [], "saliency": NSNull(), "texts": [], "read_error": true, "error": "\(error)"]
        if let d = try? JSONSerialization.data(withJSONObject: errItem),
           let s = String(data: d, encoding: .utf8) {
            lock.lock(); outputs[idx] = s; errCount += 1; lock.unlock()
        } else {
            lock.lock(); errCount += 1; lock.unlock()
        }
        if let msgData = "Vision perform error on \(path): \(error)\n".data(using: .utf8) {
            FileHandle.standardError.write(msgData)
        }
        return
    }

    var facesOut: [[String: Any]] = []
    let dw = Double(dispWidth)
    let dh = Double(dispHeight)
    for obs in faceReq.results ?? [] {
        let b = obs.boundingBox
        var faceDict: [String: Any] = ["bbox": topLeftRect(b)]
        let lEye = eyeMetrics(obs.landmarks?.leftEye, faceBox: b, dispW: dw, dispH: dh)
        let rEye = eyeMetrics(obs.landmarks?.rightEye, faceBox: b, dispW: dw, dispH: dh)
        if let le = lEye, let re = rEye {
            faceDict["eye_cx"] = (le.cx + re.cx) * 0.5
            faceDict["eye_cy"] = (le.cy + re.cy) * 0.5
            faceDict["eye_open_ratio"] = (le.openRatio + re.openRatio) * 0.5
        } else if let e = lEye ?? rEye {
            faceDict["eye_cx"] = e.cx
            faceDict["eye_cy"] = e.cy
            faceDict["eye_open_ratio"] = e.openRatio
        } else {
            faceDict["eye_cx"] = Double(b.origin.x + b.size.width * 0.5)
            faceDict["eye_cy"] = 1.0 - Double(b.origin.y + b.size.height * 0.62)
            faceDict["eye_open_ratio"] = 0.25
        }
        faceDict["mouth_open_ratio"] = mouthOpenRatio(obs.landmarks?.innerLips ?? obs.landmarks?.outerLips, faceBox: b, dispW: dw, dispH: dh)
        facesOut.append(faceDict)
    }

    var salOut: Any = NSNull()
    if #available(macOS 10.15, *), let sr = salReq,
       let salObs = sr.results?.first as? VNSaliencyImageObservation,
       let objs = salObs.salientObjects, !objs.isEmpty {
        var uRect = objs[0].boundingBox
        for obj in objs.dropFirst() {
            uRect = uRect.union(obj.boundingBox)
        }
        salOut = topLeftRect(uRect)
    }

    var textsOut: [[String: Any]] = []
    for obs in ocrReq.results ?? [] {
        if let cand = obs.topCandidates(1).first {
            var item: [String: Any] = topLeftRect(obs.boundingBox)
            item["text"] = cand.string
            item["conf"] = Double(cand.confidence)
            textsOut.append(item)
        }
    }

    let out: [String: Any] = [
        "file": path,
        "width": dispWidth,
        "height": dispHeight,
        "faces": facesOut,
        "saliency": salOut,
        "texts": textsOut
    ]
    if let data = try? JSONSerialization.data(withJSONObject: out),
       let s = String(data: data, encoding: .utf8) {
        lock.lock(); outputs[idx] = s; lock.unlock()
    }
}

for s in outputs {
    if let s = s { print(s) }
}
if errCount > 0 { exit(2) }
"""


def _src_hash() -> str:
    return hashlib.sha256(VISION_INSPECTOR_SWIFT_SRC.encode("utf-8")).hexdigest()[:12]


def ensure_vision_inspector_bin() -> Optional[Path]:
    """在 macOS 上带文件锁与原子重命名编译缓存原生 Apple Vision CLI。"""
    if platform.system() != "Darwin":
        return None
    swiftc = shutil.which("swiftc")
    if not swiftc:
        print("[vision_inspector] 未检测到 swiftc，视觉感知将回退为降级模式。", file=sys.stderr)
        return None

    cache_dir = Path.home() / ".short-video-studio" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    tag = _src_hash()
    bin_path = cache_dir / f"svs_vision_inspector_{tag}"
    if bin_path.exists() and bin_path.stat().st_size > 10000:
        return bin_path

    lock_path = cache_dir / f"svs_vision_inspector_{tag}.lock"
    lock_fd = None
    try:
        import fcntl
        lock_fd = lock_path.open("w", encoding="utf-8")
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
    except Exception:
        lock_fd = None

    try:
        if bin_path.exists() and bin_path.stat().st_size > 10000:
            return bin_path
        pid = os.getpid()
        src_tmp = cache_dir / f"svs_vision_inspector_{tag}_{pid}.swift"
        bin_tmp = cache_dir / f"svs_vision_inspector_{tag}_{pid}.tmp"
        src_tmp.write_text(VISION_INSPECTOR_SWIFT_SRC.strip() + "\n", encoding="utf-8")
        res = subprocess.run(
            [swiftc, "-O", str(src_tmp), "-o", str(bin_tmp)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        src_tmp.unlink(missing_ok=True)
        if res.returncode == 0 and bin_tmp.exists():
            os.replace(bin_tmp, bin_path)
            return bin_path
        bin_tmp.unlink(missing_ok=True)
        print(f"[vision_inspector] swiftc 编译失败: {(res.stderr or '')[-400:]}", file=sys.stderr)
        return None
    finally:
        if lock_fd is not None:
            try:
                import fcntl
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
                lock_fd.close()
            except Exception:
                pass


def compute_laplacian_sharpness(img_arr: np.ndarray) -> float:
    """计算图像灰度拉普拉斯算子方差，数值越高代表画面越锐利不虚焦。"""
    if img_arr.ndim == 3:
        gray = compute_bt709_luma(img_arr.astype(np.float32))
    else:
        gray = img_arr.astype(np.float32)
    if gray.shape[0] < 4 or gray.shape[1] < 4:
        return 0.0
    lap = (
        gray[:-2, 1:-1]
        + gray[2:, 1:-1]
        + gray[1:-1, :-2]
        + gray[1:-1, 2:]
        - 4.0 * gray[1:-1, 1:-1]
    )
    return round(float(np.var(lap)), 2)


_PERSON_SEG_SWIFT = r'''
import Foundation
import Vision
import CoreImage
import ImageIO

let args = Array(CommandLine.arguments.dropFirst())
if args.count < 2 { exit(2) }
let inUrl = URL(fileURLWithPath: args[0])
let outUrl = URL(fileURLWithPath: args[1])

guard #available(macOS 12.0, *),
      let src = CGImageSourceCreateWithURL(inUrl as CFURL, nil),
      let cgImg = CGImageSourceCreateImageAtIndex(src, 0, nil) else {
    exit(1)
}
var cgOrientation = CGImagePropertyOrientation.up
if let props = CGImageSourceCopyPropertiesAtIndex(src, 0, nil) as? [CFString: Any],
   let rawOri = props[kCGImagePropertyOrientation] as? UInt32,
   let parsedOri = CGImagePropertyOrientation(rawValue: rawOri) {
    cgOrientation = parsedOri
}
let swapped = (cgOrientation == .left || cgOrientation == .right || cgOrientation == .leftMirrored || cgOrientation == .rightMirrored)
let dispW = swapped ? cgImg.height : cgImg.width
let dispH = swapped ? cgImg.width : cgImg.height

let req = VNGeneratePersonSegmentationRequest()
req.qualityLevel = .balanced
req.outputPixelFormat = kCVPixelFormatType_OneComponent8
let handler = VNImageRequestHandler(cgImage: cgImg, orientation: cgOrientation, options: [:])
do {
    try handler.perform([req])
    guard let obs = req.results?.first as? VNPixelBufferObservation else { exit(1) }
    let ciMask = CIImage(cvPixelBuffer: obs.pixelBuffer)
    let sx = CGFloat(dispW) / max(1.0, ciMask.extent.width)
    let sy = CGFloat(dispH) / max(1.0, ciMask.extent.height)
    let scaled = ciMask.transformed(by: CGAffineTransform(scaleX: sx, y: sy))
    let ctx = CIContext()
    guard let outCg = ctx.createCGImage(scaled, from: CGRect(x: 0, y: 0, width: dispW, height: dispH)),
          let dest = CGImageDestinationCreateWithURL(outUrl as CFURL, "public.png" as CFString, 1, nil) else {
        exit(1)
    }
    CGImageDestinationAddImage(dest, outCg, nil)
    if !CGImageDestinationFinalize(dest) { exit(1) }
} catch {
    exit(1)
}
'''


def _ensure_person_seg_bin() -> Optional[Path]:
    if platform.system() != "Darwin" or not shutil.which("swiftc"):
        return None
    bin_dir = Path.home() / ".short-video-studio" / "cache"
    bin_dir.mkdir(parents=True, exist_ok=True)
    sig = hashlib.sha256(_PERSON_SEG_SWIFT.encode("utf-8")).hexdigest()[:10]
    bin_path = bin_dir / f"svs_person_seg_{sig}"
    if bin_path.is_file() and os.access(bin_path, os.X_OK):
        return bin_path
    src_tmp = bin_dir / f"svs_person_seg_{os.getpid()}.swift"
    bin_tmp = bin_dir / f"svs_person_seg_{os.getpid()}.tmp"
    try:
        src_tmp.write_text(_PERSON_SEG_SWIFT, encoding="utf-8")
        res = subprocess.run(
            ["swiftc", "-O", str(src_tmp), "-o", str(bin_tmp), "-framework", "Vision", "-framework", "CoreImage", "-framework", "ImageIO"],
            capture_output=True, text=True, check=False,
        )
        if res.returncode == 0 and bin_tmp.is_file():
            os.replace(bin_tmp, bin_path)
            return bin_path
    except Exception:
        pass
    finally:
        src_tmp.unlink(missing_ok=True)
        bin_tmp.unlink(missing_ok=True)
    return None


def segment_person_mask(image_path: Path, out_mask_png: Path) -> bool:
    """macOS 原生 Apple Vision 前景人像分割（零外部依赖零 API 费），输出灰度蒙版 PNG；非 macOS 优雅返回 False。"""
    seg_bin = _ensure_person_seg_bin()
    if seg_bin is None or not image_path.is_file():
        return False
    res = subprocess.run([str(seg_bin), str(image_path), str(out_mask_png)], capture_output=True, check=False)
    return res.returncode == 0 and out_mask_png.is_file() and out_mask_png.stat().st_size > 128


def _fallback_inspect_single(img_path: Path) -> Dict[str, Any]:
    """非 macOS 或 Vision CLI 不可用时的纯 Python 梯度显著性降级检测（应用 EXIF 旋转）。"""
    try:
        with Image.open(img_path) as im:
            im_t = ImageOps.exif_transpose(im)
            w, h = im_t.size
            small = im_t.convert("L").resize((120, max(12, int(round(120 * h / max(1, w))))))
            arr = np.asarray(small, dtype=np.float32)
    except Exception:
        return {
            "file": str(img_path),
            "width": 0,
            "height": 0,
            "faces": [],
            "saliency": None,
            "texts": [],
            "backend": "fallback",
            "read_error": True,
        }

    gx = np.abs(np.diff(arr, axis=1, prepend=arr[:, :1]))
    gy = np.abs(np.diff(arr, axis=0, prepend=arr[:1, :]))
    grad = gx + gy
    thresh = float(np.percentile(grad, 82))
    ys, xs = np.where(grad >= thresh)
    sal = None
    if len(xs) > 10:
        sh, sw = arr.shape
        x0 = float(np.percentile(xs, 10)) / sw
        x1 = float(np.percentile(xs, 90)) / sw
        y0 = float(np.percentile(ys, 10)) / sh
        y1 = float(np.percentile(ys, 90)) / sh
        sal = {"x": round(x0, 4), "y": round(y0, 4), "w": round(max(0.05, x1 - x0), 4), "h": round(max(0.05, y1 - y0), 4)}
    return {
        "file": str(img_path),
        "width": int(w),
        "height": int(h),
        "faces": [],
        "saliency": sal,
        "texts": [],
        "backend": "numpy_gradient_fallback",
    }


def inspect_images(image_paths: List[Path], batch_size: int = 32) -> Dict[str, Dict[str, Any]]:
    """
    批量检测图片的人脸、双眼锚点/睁眼比、主体显著性与 OCR 文字框。
    返回映射: {str(path): result_dict}
    """
    if not image_paths:
        return {}
    vision_bin = ensure_vision_inspector_bin()
    results: Dict[str, Dict[str, Any]] = {}

    if vision_bin is not None:
        for i in range(0, len(image_paths), batch_size):
            chunk = image_paths[i : i + batch_size]
            cmd = [str(vision_bin)] + [str(p) for p in chunk]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            if res.stdout:
                for line in res.stdout.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        obj["backend"] = "apple_vision_read_error" if obj.get("read_error") else "apple_vision"
                        results[obj["file"]] = obj
                    except Exception:
                        continue
            if res.returncode != 0:
                print(f"[vision_inspector] Apple Vision 部分或全部帧报错 ({res.returncode}): {(res.stderr or '')[-300:]}", file=sys.stderr)

    for p in image_paths:
        key = str(p)
        if key not in results:
            results[key] = _fallback_inspect_single(p)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="跨平台视觉原材分析器 (人脸/双眼/显著性/OCR)")
    parser.add_argument("images", nargs="+", help="待检测图片路径列表")
    args = parser.parse_args()
    paths = [Path(x) for x in args.images]
    out = inspect_images(paths)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
