# NOTICE

## 上游模板

本仓库的知识库基于以下开源项目整理：

- **项目**：DaShuJuZhiDaPingZhanShi（大数据展示 · 各类大屏模板）
- **地址**：https://gitee.com/lvyeyou/DaShuJuZhiDaPingZhanShi
- **作者**：Lang（lvyeyou）
- **许可**：MIT License，Copyright (c) 2019 Lang
- **抓取版本**：commit `75a203b`，2026-11-26

本仓库**不包含**上游项目的源码副本。`vendor/dashuju-templates/` 由
`scripts/fetch-templates.mjs` 在使用者本地克隆，且已在 `.gitignore` 中忽略。
`knowledge/` 中的文字为原创拆解；`assets/previews/` 为上游截图的压缩缩略图，
用于模板选型参考，版权归原作者所有，遵循上游 MIT 许可。

如需在自己项目中使用上游模板源码，请保留其 MIT 版权声明。

## 地图数据

- `starter/data/china.json`：中国省级行政区 GeoJSON，来源于
  [DataV.GeoAtlas](https://datav.aliyun.com/portal/school/atlas/area_selector)。
  仅用于示例/演示；生产使用请确认数据授权与审图号要求。

## 字体

- **Rajdhani**：SIL Open Font License 1.1，版权归原作者所有。
  文件位于 `starter/vendor/fonts/`，许可说明见同目录 `OFL.txt`。
  https://fonts.google.com/specimen/Rajdhani

## 第三方库

- **Apache ECharts 5.5.1**：Apache License 2.0。
  文件位于 `starter/vendor/echarts.min.js`。

## 本仓库

代码与文档：MIT License，Copyright (c) 2026 jxy162。
