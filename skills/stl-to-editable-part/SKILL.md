---
name: stl-to-editable-part
description: Convert STL meshes to editable native SolidWorks SLDPRT parts with fully defined sketches and driving dimensions. Use for STL 转可编辑 SolidWorks、STL 转 SLDPRT、STL 转 SW 原生零件 or parameterizing a supplied STL. For STL to STEP alone or STEP-only input use the corresponding separate skill.
---

# STL 转可编辑 SolidWorks 零件

从 STL 交付独立的 `.SLDPRT`。大平面应能整面选取，能可靠恢复的孔和圆角应使用解析几何。以原生拉伸、切除、孔等特征驱动形体，并以可修改的尺寸和几何关系完全定义建模草图。

1. 确认输入、单位、左右件和交付位置。STL 没有单位，优先用已知尺寸确认比例。按毫米推定时，在交付中说明。每件使用单独的工作目录。
2. 在 Windows 上通过 DeepSeek Harness 的 PowerShell 工具运行 [scripts/run-on-windows.ps1](scripts/run-on-windows.ps1)。从技能加载结果取得技能目录，使用其中脚本的绝对路径。首次运行先使用 `-Check`，缺少依赖时按 [依赖配置](references/deepseek-harness.md) 处理。脚本验证网格，合并共面三角面，重建能可靠拟合的直通孔，再尝试在本机 SolidWorks 中通过 FeatureWorks 生成特征。校验通过才写出 `.SLDPRT`。

   ```powershell
   & '<技能目录>\scripts\run-on-windows.ps1' -Source '.\零件.stl' -Destination '.\零件-可编辑.SLDPRT' -WorkDir '.\work\零件' -Units mm
   ```

3. 自动路径卡住时从已验证的阶段继续。STEP 的 API 导入失败可用桌面 SolidWorks 打开脚本生成的 `geometry.step`，保存工作副本并传入 `-ImportedPart`。FeatureWorks 未能生成完整特征树时，按 [原生重建和验收](references/workflow.md) 实测剖面、槽和孔，传入 `-Plan` 重建。用户明确要求只能用 FeatureWorks 时，报告其具体限制，取得同意后再切换路线。明显圆角、盲孔或其他未覆盖曲面按 [圆角与过渡曲面](references/smooth-surfaces.md) 分析，核对后再建立解析几何基线。
4. 保存、重开并强制重建。检查实体、轮廓、孔位、草图约束、驱动尺寸和下游特征。用不保存的工作副本试改代表性尺寸，查看几何随之变化，再恢复。交付经过核验的 `.SLDPRT`，说明尺寸假设、采用的识别或重建路线以及未恢复的几何。中间 STEP、识别候选和日志留在工作目录。

脚本适用于 Windows 上的本机 SolidWorks。普通网格管线支持二进制或 ASCII 的单个闭合定向流形。自动圆柱恢复覆盖两张平行面之间沿输入 Y 轴、两端可匹配的直通孔。拉伸重建脚本可按实测计划创建单实体平面凸台与切除。其他形体需要另行测量并创建相应的原生特征。

在 DeepSeek Harness 中使用本机工作区。把中间文件和输出放在会话允许写入的目录。若 shell 权限阻止启动 CAD 或读取文件，遵循 Harness 的授权流程。Python 与 OCP 的检查方法见 [DeepSeek Harness 运行方式](references/deepseek-harness.md)。
