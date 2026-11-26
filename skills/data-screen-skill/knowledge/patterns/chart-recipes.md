# 图表配方（ECharts 5）

> 选图先看「要回答什么问题」，再看「数据长什么样」。
> 下面的 option 都是完整可运行的片段，直接贴进 `setOption` 即可。

## 0. 选型表

| 你想表达 | 用 | 不要用 |
|---|---|---|
| 随时间变化 | 折线 / 柱线复合 | 饼图 |
| 类别对比（≤12 类） | 横向条形（可排序） | 3D 柱 |
| 占比（≤6 类） | 环形图 / 堆叠条 | 多环饼图 |
| 占比随时间 | 堆叠面积 | 多个饼图 |
| 排名 | 横向条形 + 数值标签 | 词云 |
| 单指标达成 | 仪表盘 / 进度条 | 雷达 |
| 多维评分（5–8 维） | 雷达 | 饼图 |
| 空间分布 | 地图 + 涟漪/热力 | 散点（无底图） |
| 流向/关系 | 飞线 / 关系图 | 桑基（除非真有多级流转） |
| 转化流程 | 漏斗 | 饼图 |
| 异常与阈值 | 折线 + markLine/markArea | 仪表盘堆叠 |

## 1. 全局主题（一次注册，全屏统一）

```js
const T = {
  bg:"#030a16", panel:"rgba(10,30,58,.62)", line:"rgba(74,158,255,.18)",
  accent:"#35d6ff", accent2:"#2e7bff", warm:"#ffc93c",
  danger:"#ff4d6d", ok:"#2fe6a8", text:"#e8f3ff", dim:"#7d95b5"
};
echarts.registerTheme("screen", {
  backgroundColor:"transparent",
  textStyle:{ color:T.dim, fontFamily:"PingFang SC, Microsoft YaHei, sans-serif" },
  color:[T.accent,T.accent2,T.warm,T.ok,"#8b7cff",T.danger],
  title:{ textStyle:{ color:T.text } },
  legend:{ textStyle:{ color:T.dim } },
  tooltip:{
    backgroundColor:"rgba(4,14,28,.94)", borderColor:"rgba(53,214,255,.35)",
    textStyle:{ color:T.text }
  },
  categoryAxis:{ axisLine:{ lineStyle:{ color:"rgba(125,149,181,.28)" } },
    axisLabel:{ color:T.dim }, splitLine:{ show:false } },
  valueAxis:{ axisLine:{ show:false }, axisLabel:{ color:T.dim },
    splitLine:{ lineStyle:{ color:"rgba(125,149,181,.12)", type:"dashed" } } }
});
echarts.init(el, "screen", { renderer:"canvas" });
```

## 2. 柱状图（渐变 + 圆角 + 背景槽）

```js
{
  grid:{ top:34, left:6, right:14, bottom:4, containLabel:true },
  xAxis:{ type:"category", data:["西湖","余杭","拱墅","上城","滨江"],
          axisTick:{ show:false }, axisLine:{ lineStyle:{ color:"rgba(125,149,181,.28)" } },
          axisLabel:{ color:"#7d95b5", fontSize:11 } },
  yAxis:{ type:"value", splitNumber:4, axisLabel:{ color:"#7d95b5" },
          splitLine:{ lineStyle:{ color:"rgba(125,149,181,.12)", type:"dashed" } } },
  series:[{
    type:"bar", barWidth:10, showBackground:true,
    backgroundStyle:{ color:"rgba(125,149,181,.10)", borderRadius:[1,1,0,0] },
    itemStyle:{
      borderRadius:[1,1,0,0],
      color:new echarts.graphic.LinearGradient(0,0,0,1,[
        { offset:0, color:"rgba(53,214,255,.95)" },
        { offset:1, color:"rgba(53,214,255,.18)" }
      ])
    },
    data:[286,254,208,186,164]
  }]
}
```

## 3. 横向排名（最推荐用于「TOP N」）

```js
{
  grid:{ top:4, left:6, right:44, bottom:2, containLabel:true },
  xAxis:{ type:"value", show:false, max:(v)=>v.max*1.15 },
  yAxis:{ type:"category", inverse:true, data:names,
          axisLine:{ show:false }, axisTick:{ show:false },
          axisLabel:{ color:"#7d95b5", fontSize:12 } },
  series:[{
    type:"bar", barWidth:9, showBackground:true,
    backgroundStyle:{ color:"rgba(125,149,181,.10)", borderRadius:2 },
    itemStyle:{ borderRadius:[0,2,2,0],
      color:new echarts.graphic.LinearGradient(0,0,1,0,[
        { offset:0, color:"rgba(53,214,255,.35)" },
        { offset:1, color:"#35d6ff" }
      ]) },
    label:{ show:true, position:"right", color:"#e8f3ff", fontFamily:"Rajdhani, sans-serif" },
    data:values
  }]
}
```
> 数值必须显示。大屏没有 hover，tooltip 不能作为唯一读数方式。

## 4. 折线 / 柱线复合

```js
{
  color:["#35d6ff","#ffc93c"],
  tooltip:{ trigger:"axis", axisPointer:{ type:"shadow" } },
  legend:{ right:0, top:0, icon:"roundRect", itemWidth:8, itemHeight:8 },
  xAxis:{ type:"category", boundaryGap:true, data:days },
  yAxis:[{ type:"value" }, { type:"value", splitLine:{ show:false } }],
  series:[
    { name:"受理", type:"bar", barWidth:10,
      itemStyle:{ borderRadius:[1,1,0,0],
        color:new echarts.graphic.LinearGradient(0,0,0,1,[
          {offset:0,color:"rgba(53,214,255,.95)"},{offset:1,color:"rgba(53,214,255,.18)"}]) },
      data:bars },
    { name:"办结率", type:"line", yAxisIndex:1, smooth:.35, showSymbol:false,
      lineStyle:{ width:2, shadowBlur:10, shadowColor:"rgba(255,201,60,.5)" },
      areaStyle:{ color:new echarts.graphic.LinearGradient(0,0,0,1,[
        {offset:0,color:"rgba(255,201,60,.28)"},{offset:1,color:"rgba(255,201,60,0)"}]) },
      data:rates }
  ]
}
```
> 双 Y 轴只在单位不同时使用，且必须用图例/轴标题标清单位。

## 5. 环形图 + 中心总计

```js
{
  graphic:[
    { type:"text", left:"center", top:"42%", style:{
        text:"1,286", fill:"#e8f3ff", font:"600 26px Rajdhani", textAlign:"center" } },
    { type:"text", left:"center", top:"56%", style:{
        text:"事件总数", fill:"#4a6285", font:"11px sans-serif", textAlign:"center" } }
  ],
  series:[{
    type:"pie", radius:["56%","76%"], center:["50%","52%"],
    avoidLabelOverlap:true, padAngle:2,
    itemStyle:{ borderColor:"rgba(3,10,22,.9)", borderWidth:2, borderRadius:2 },
    label:{ show:false }, labelLine:{ show:false },
    emphasis:{ scale:true, scaleSize:5 },
    data:[{name:"市容",value:386},{name:"交通",value:312},{name:"安全",value:186}]
  }]
}
```
> `graphic` 的 `left:"center"` 在 ECharts 5 中是相对容器居中；若与图例并排，用百分比并加 `textAlign:"center"`。
> 环形图最多 6 段；超过就改为「条形排名」或合并「其他」。

## 6. 雷达（多维评分）

```js
{
  radar:{
    center:["50%","56%"], radius:"66%",
    indicator:[{name:"响应",max:100},{name:"质量",max:100},{name:"满意",max:100},{name:"协同",max:100},{name:"透明",max:100}],
    axisName:{ color:"#7d95b5", fontSize:10.5 },
    splitLine:{ lineStyle:{ color:"rgba(125,149,181,.16)" } },
    splitArea:{ areaStyle:{ color:["rgba(53,214,255,.03)","transparent"] } },
    axisLine:{ lineStyle:{ color:"rgba(125,149,181,.16)" } }
  },
  series:[{
    type:"radar", symbolSize:4,
    data:[
      { name:"本月", value:[92,88,96,84,90],
        lineStyle:{ color:"#35d6ff" }, itemStyle:{ color:"#35d6ff" },
        areaStyle:{ color:"rgba(53,214,255,.18)" } },
      { name:"上月", value:[86,84,92,79,85],
        lineStyle:{ color:"#ffc93c" }, itemStyle:{ color:"#ffc93c" },
        areaStyle:{ color:"rgba(255,201,60,.12)" } }
    ]
  }]
}
```

## 7. 仪表盘（单指标达成）

```js
{
  series:[{
    type:"gauge", startAngle:214, endAngle:-34, min:0, max:100,
    radius:"92%", center:["50%","58%"],
    progress:{ show:true, width:9, roundCap:true,
      itemStyle:{ color:new echarts.graphic.LinearGradient(0,0,1,0,[
        {offset:0,color:"#35d6ff"},{offset:1,color:"#2e7bff"}]) } },
    axisLine:{ roundCap:true, lineStyle:{ width:9, color:[[1,"rgba(125,149,181,.16)"]] } },
    axisTick:{ show:false }, splitLine:{ show:false }, axisLabel:{ show:false },
    pointer:{ show:false }, anchor:{ show:false },
    title:{ offsetCenter:[0,"34%"], color:"#7d95b5", fontSize:11 },
    detail:{ offsetCenter:[0,"-2%"], valueAnimation:true, formatter:"{value}%",
      color:"#e8f3ff", fontSize:34, fontFamily:"Rajdhani", fontWeight:600 },
    data:[{ value:81.1, name:"按时办结率" }]
  }]
}
```
> 一个面板只放 1 个仪表盘。3 个并排的仪表盘 = 3 个进度条更清楚。

## 8. 中国地图（ECharts 5 + GeoJSON）

```js
// 1) 加载并注册（只做一次）
const geo = await fetch("./data/china.json").then(r => r.json());
echarts.registerMap("china", geo);

// 2) option
{
  geo:{ map:"china", roam:false, zoom:1.18, center:[104,36],
        itemStyle:{ areaColor:"transparent", borderColor:"transparent" }, silent:true },
  series:[
    { type:"map", map:"china", roam:false, zoom:1.18, center:[104,36],
      itemStyle:{
        areaColor:new echarts.graphic.LinearGradient(0,0,0,1,[
          {offset:0,color:"#0b2b56"},{offset:1,color:"#08203c"}]),
        borderColor:"rgba(53,214,255,.42)", borderWidth:.8,
        shadowColor:"rgba(53,214,255,.28)", shadowBlur:18
      },
      emphasis:{ label:{ color:"#fff", fontSize:11 },
        itemStyle:{ areaColor:"rgba(53,214,255,.28)", borderColor:"#35d6ff" } },
      label:{ show:true, color:"rgba(125,149,181,.85)", fontSize:9 },
      data:[{ name:"浙江省", value:286 }]
    },
    { type:"effectScatter", coordinateSystem:"geo",
      rippleEffect:{ brushType:"stroke", scale:3.2, period:3 },
      symbolSize:v=>Math.max(6,Math.min(22,Math.sqrt(v[2])*2.2)),
      itemStyle:{ color:"#ff4d6d", shadowBlur:12, shadowColor:"#ff4d6d" },
      data:[{ name:"杭州", value:[120.155,30.274,286] }] },
    { type:"lines", coordinateSystem:"geo",
      effect:{ show:true, period:4, trailLength:.6, symbol:"arrow", symbolSize:5, color:"#ffc93c" },
      lineStyle:{ color:"rgba(255,201,60,.35)", width:1, curveness:.25 },
      data:[{ coords:[[120.155,30.274],[121.473,31.23]] }] }
  ]
}
```

**要点**
- `value:[lng,lat,value]` 顺序不能反。坐标系必须与 GeoJSON 一致（国测局数据用 GCJ-02，GPS 用 WGS-84，混用会偏移 300–500m）。
- 省份名必须与 GeoJSON 的 `properties.name` 完全一致（如「浙江省」不是「浙江」）。
- 地图不显示时，先查 `echarts.getMap("china")` 是否为空、GeoJSON 是否是 `FeatureCollection`。
- 内网/无外网：把 GeoJSON 放本地（starter 已带 `data/china.json`）。

## 9. 漏斗 / 转化

```js
{
  series:[{
    type:"funnel", left:"8%", right:"8%", top:8, bottom:8, minSize:"22%",
    sort:"descending", gap:2,
    label:{ show:true, position:"inside", color:"#04101f", fontSize:12, fontWeight:600,
      formatter:"{b} {c}" },
    itemStyle:{ borderWidth:0, borderRadius:2 },
    emphasis:{ label:{ fontSize:13 } },
    data:[{name:"曝光",value:12000},{name:"点击",value:6200},{name:"加购",value:2100},{name:"下单",value:860}]
  }]
}
```
> 漏斗的「转化率」要单独标注（在 label 里算 `value/prev`），否则观众要自己心算。

## 10. 进度条（设备使用率/负载）

```js
{
  grid:{ left:60, right:40, top:10, bottom:10 },
  xAxis:{ type:"value", max:100, show:false },
  yAxis:{ type:"category", data:["1号机","2号机","3号机"], axisLine:{show:false},
          axisTick:{show:false}, axisLabel:{color:"#7d95b5"} },
  series:[
    { type:"bar", barWidth:10, showBackground:true,
      backgroundStyle:{ color:"rgba(125,149,181,.12)", borderRadius:6 },
      itemStyle:{ borderRadius:6,
        color:new echarts.graphic.LinearGradient(0,0,1,0,[
          {offset:0,color:"rgba(53,214,255,.4)"},{offset:1,color:"#35d6ff"}]) },
      label:{ show:true, position:"right", formatter:"{c}%", color:"#e8f3ff" },
      data:[70,46,69] }
  ]
}
```
> 阈值变色：在 `data` 里对每一项单独设置 `itemStyle.color`（<60 绿、60–85 黄、>85 红）。

## 11. 关系图（系统拓扑）

```js
{
  tooltip:{},
  series:[{
    type:"graph", layout:"force", roam:false,
    force:{ repulsion:220, edgeLength:120, gravity:.08 },
    symbolSize:node=>node.value? Math.max(18,node.value/8) : 26,
    itemStyle:{ color:"#0b2b56", borderColor:"#35d6ff", borderWidth:1.5,
      shadowBlur:12, shadowColor:"rgba(53,214,255,.5)" },
    lineStyle:{ color:"rgba(53,214,255,.28)", width:1, curveness:.12 },
    label:{ show:true, color:"#cfe6ff", fontSize:10 },
    emphasis:{ focus:"adjacency", lineStyle:{ width:2, color:"#35d6ff" } },
    data:[{name:"数据中心",value:100,symbolSize:48},{name:"系统一",value:60}],
    links:[{source:"数据中心",target:"系统一"}]
  }]
}
```
**稳定输出**：力导向图每次刷新会重新布局，长时间投屏会「抖」。生产环境用 `layout:"none"` + 预付 `x/y`，或只在首次布局后固定坐标。

## 12. 3D 地图（echarts-gl，谨慎）

```js
// echarts 5.4 + echarts-gl 2.0
{
  geo3D:{ map:"china", boxHeight:6, regionHeight:2,
    itemStyle:{ color:"#0b2b56", borderColor:"rgba(74,222,254,.6)" },
    viewControl:{ distance:120, alpha:40, beta:0, autoRotate:false },
    light:{ main:{ intensity:1.2, shadow:true }, ambient:{ intensity:.4 } } },
  series:[{ type:"bar3D", coordinateSystem:"geo3D",
    data:[{name:"杭州",value:[120.155,30.274,286]}] }]
}
```
**代价**：包体积 +700KB、低配机器 20–30fps、LED 拼接可能花屏。
**必须准备 2D 降级**：`if (低端设备 || 不支持 WebGL) 渲染 map`。

## 13. 不是图表的组件

| 组件 | 做法 | 要点 |
|---|---|---|
| 大数字翻牌 | DOM + `requestAnimationFrame` 缓动 | `font-variant-numeric: tabular-nums`，避免宽度跳动 |
| 滚动表格 | 克隆首行 + `translateY` + 定时复位 | 行高固定；`prefers-reduced-motion` 时停止 |
| 跑马灯 | 内容复制两份 + rAF 位移 + 取模 | 悬停暂停；不要用 `<marquee>` |
| 实时日志 | 固定高度 + 追加 + 超出行数删除 | 只在底部追加，避免整表重绘 |
| 状态灯 | 7px 圆点 + 呼吸动画 | 同时给文字状态，不只靠颜色 |

## 14. 性能红线

- 单页图表 ≤ 20 个；每个 canvas ≤ 2 万点。
- 大数据散点用 `large:true`、`progressive:0`、`animation:false`。
- 地图点位 > 500 时关闭 `rippleEffect`，用 `scatter` + 热力。
- 轮询刷新用 `setOption(option, { notMerge:false })` 保留动画；结构变化才 `notMerge:true`。
- 页面隐藏时暂停定时器/动画（`document.hidden`）。
- 字体加载完成后再 `chart.resize()`，否则文字宽度计算错误。
