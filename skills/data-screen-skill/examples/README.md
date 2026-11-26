# 示例

## starter = 可运行示例

`starter/` 本身就是一套完整的示例大屏（城市运行指挥中心，A1 布局）：

```bash
node scripts/serve.mjs starter
# http://localhost:5173/?static=1   （static=1 关闭动画，便于截图）
```

![starter](../assets/screenshot-starter.png)

它演示了：

- 6 个 KPI + 数字滚动
- 中国地图（省份着色 + 涟漪点 + 飞线）
- 柱线复合、玫瑰环、横向排名、仪表盘、堆叠条、雷达
- 滚动工单、告警列表、跑马灯播报
- 4 个 Tab 视图（数据来自 `views.*`）
- 状态灯（示例/实时/延迟/失败）
- `?static=1` 截图模式
- `prefers-reduced-motion` 降级

## city-ops-brief.md = 需求 brief 示例

展示「从一句用户需求」到「可执行 brief」的样子，
对应 `knowledge/workflow/brief-extraction.md` 的输出格式。

## 自己生成

```bash
node scripts/new-screen.mjs --out screens/my-screen --title "我的数据大屏" --theme green
```
