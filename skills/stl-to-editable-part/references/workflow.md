# 原生重建和验收

## 运行环境

Python 3.10+、NumPy、Open CASCADE 的 `OCP` 绑定、Windows PowerShell 5.1 和本机 SolidWorks。已验证环境是 Python 3.12、`cadquery-ocp-novtk==7.9.3.1.1`、SolidWorks 2025 SP5.0。先验证可用的 Python 能导入 NumPy 和 OCP。已有局部依赖可通过 `--ocp-path` 指定。SolidWorks 默认由安装信息定位，也可用 `--sw-root`。依赖和网格排查见 [重建与排查](reconstruction.md)。

## 续接任务

`--prepare-only` 在 `--work-dir` 生成供测量的 `geometry.step`、`geometry.json` 和记录源 STL 哈希、单位及孔处理选项的 `mesh-request.json`。准备过程可独立运行。实测后用相同源与选项加 `--plan`，重用中间 STEP。变更单位、孔径或输入后使用新的工作目录。

- `--holes auto` 尝试恢复脚本支持的圆孔。 `--holes require` 适合明确必须恢复的可识别直通孔。 `--hole-diameter-mm` 只在原孔实测与指定直径吻合时采用。 `--holes keep` 保留源孔分面作为工作几何。若用户明确要求平滑孔或圆角，检查 `geometry.json` 与实际 B-Rep，继续重建仍有分面的指定位置。
- 若脚本在 STEP 导入处停止，从本机桌面打开该工作目录的 `geometry.step`，保存为 `imported.SLDPRT`，以相同参数加 `--imported-part imported.SLDPRT` 重跑。脚本在工作副本上断开 3D Interconnect 链接，并核对导入实体与 STEP 的外包尺寸和体积。不要把另一件形状相近的零件当作基线。
- 从工作 STEP 测量轮廓并写建模计划。用 `--plan plan.json` 重建，有指定模板时加 `--template part.prtdot`。每次原生尝试有自己的 `native-*` 子目录，包含独立基线、运行日志和验证预览。
- 如果模型已有经过实测验证的复杂曲面基线，或需要旋转、放样、钣金、多实体等超出这条脚本路线的特征，直接使用本技能的 SolidWorks 辅助脚本或原生 CAD 操作。保持源网格、曲面基线和交付零件之间可核验的几何对应。

## 复用已验收结果

转换脚本通过 SolidWorks 验收后，在对应 `native-*` 目录写入 `verified-result.json` 并输出其路径。把记录和同目录的 `editable.SLDPRT` 一起保留。再次交付同一几何和验收结果时，可以直接复制以前通过验收的文件。入口核对源 STL 和零件的 SHA-256、源单位及孔处理选项。

```powershell
& '<技能目录>\scripts\run-on-windows.ps1' -Source '.\零件.stl' `
    -Destination '.\零件-副本.SLDPRT' -Units mm `
    -ReuseVerified '<上一任务的 native-目录>\verified-result.json'
```

复用要求信任原任务的验收记录。只有当原来的验收覆盖本次要求时才复用。源 STL、单位、孔设置、建模意图或验收要求变化时，应重建。已有由旧版或自定义脚本产生的零件时，可使用该任务保存的方案重新运行支持它的建模脚本并验收。

## 原生特征计划

用 Open CASCADE 等几何内核读取工作 STEP 的 B-Rep，截取主轮廓、提取直线边界、测量孔轴与半径。将可编辑参数落实到原生特征，区分左右镜像几何。试图恢复原设计尺寸时，用来源尺寸或拟合偏差说明依据。

`plan.json` 使用世界坐标，单位 mm。 `axis` 为 0=X、1=Y、2=Z，分别使用右视、上视、前视基准面。所有草图点在相应世界坐标为 0 的基准面上。 `low` 和 `high` 给出特征沿该轴的起止坐标。 `polygons` 由有序轮廓点组成，脚本闭合首尾。 `circles` 中每项为 `[x,y,z,r]`。首个特征为凸台，随后可添加凸台或切除。

```json
{
  "features": [
    {"name":"底板","axis":2,"low":0,"high":6,"cut":false,
     "polygons":[[[0,0,0],[30,0,0],[30,20,0],[0,20,0]]]},
    {"name":"通孔","axis":2,"low":0,"high":6,"cut":true,
     "circles":[[10,10,0,3],[20,10,0,3]]}
  ]
}
```

## 验收

辅助脚本 [solidworks-part.ps1](../scripts/solidworks/solidworks-part.ps1) 需由 Windows PowerShell 5.1 的 STA 模式执行。`--plan` 使用 `RebuildValidate`，在同一 SolidWorks 连接里保存、关闭并重开候选，再使用和 `Validate` 相同的验收流程。验收要求单一有效实体、完全定义且有驱动尺寸的草图和关联特征，检测剩余导入主体，并做几何基线的双向实体差。`Audit` 可单独列出尺寸名、草图和实体信息。临时改动可以指定 `--edit-dimension 'D1@草图名'`，默认尝试代表性驱动尺寸并恢复原值。关键孔径、曲面和设计参数还应按用户要求单独核对。预览默认写到原生工作目录，可用 `-NoPreview` 跳过截图。

默认包围盒允许差 0.001 mm，体积及双向布尔差容差 0.01 mm³。先按源 STL 精度、真实几何变化及用户需求判断是否调整，记录依据。适用情况下核对最终孔轴、直径、深度、圆角半径和连接。回读通过后只交付最终 SLDPRT。
