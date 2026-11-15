---
name: stl-to-editable-part
description: Convert STL meshes to editable native SolidWorks SLDPRT parts with fully defined sketches and driving dimensions. Use for STL 转可编辑 SolidWorks、STL 转 SLDPRT、STL 转 SW 原生零件 or parameterizing a supplied STL. For STL to STEP alone or STEP-only input use the corresponding separate skill.
---

# STL 转可编辑 SolidWorks 零件

从 STL 交付独立的 `.SLDPRT`。大平面应能整面选取，能可靠恢复的孔和圆角应使用解析几何。以原生拉伸、切除、孔等特征驱动形体，并以可修改的尺寸和几何关系完全定义建模草图。

1. 确认输入、单位、左右件和交付位置。按毫米推定时，在交付中说明。每件使用单独的工作目录，续接同一任务时复用它。
2. 重出同一份已验收零件时，用 `-ReuseVerified` 传入原任务的 `verified-result.json`，见 [复用已验收结果](references/workflow.md#复用已验收结果)。已有实测方案时直接传入 `-Plan`。新件从 `-PrepareOnly` 开始，按 [原生特征计划](references/workflow.md#原生特征计划) 和 [光滑曲面验证](references/smooth-surfaces.md) 测量几何，再创建 SolidWorks 原生特征。含复杂曲面的零件使用相应原生特征和适用的几何基线。

   ```powershell
   & '<技能目录>\scripts\run-on-windows.ps1' -Source '.\零件.stl' -WorkDir '.\work\零件' -Units mm -PrepareOnly
   # 实测并写好 plan.json 后运行
   & '<技能目录>\scripts\run-on-windows.ps1' -Source '.\零件.stl' -Destination '.\零件-可编辑.SLDPRT' -WorkDir '.\work\零件' -Units mm -Plan '.\work\零件\plan.json'
   ```

3. 在 Windows 上从技能加载结果获取入口绝对路径。按方案建模时，脚本在同一 SolidWorks 连接里重建和验收。仅在环境尚未确认或依赖报错时用 `-Check`，见 [依赖配置](references/deepseek-harness.md)。失败后按阶段日志从已有几何基线继续。缺少可辨识的圆角边时，先根据端点、曲线类型和邻面定位，再提交选边。
4. 新建的候选保存后重开并强制重建。检查实体、轮廓、关键孔位与圆角、草图完全定义、驱动尺寸及下游特征。试改代表性尺寸，确认形体变化后恢复。脚本已有验收日志时，直接引用结果。多版候选先核对有变化的区域，对最终候选执行完整几何比对。已有通过结果且候选和基线哈希相同，可以沿用。交付核验后的 `.SLDPRT` 并说明尺寸假设和任何未恢复的几何。

脚本适用于 Windows 上的本机 SolidWorks。普通网格管线支持二进制或 ASCII 的单个闭合定向流形。自动圆柱恢复覆盖两张平行面之间沿输入 Y 轴、两端可匹配的直通孔。拉伸重建脚本可按实测计划创建单实体平面凸台与切除。其他形体需要另行测量并创建相应的原生特征。

在 DeepSeek Harness 中使用本机工作区。把中间文件和输出放在会话允许写入的目录。若 shell 权限阻止启动 CAD 或读取文件，遵循 Harness 的授权流程。Python 与 OCP 的检查方法见 [DeepSeek Harness 运行方式](references/deepseek-harness.md)。
