# 原生重建和验收

## 运行环境

Python 3.10+、NumPy、Open CASCADE 的 `OCP` 绑定、Windows PowerShell 5.1 和本机 SolidWorks。已验证环境是 Python 3.12、`cadquery-ocp-novtk==7.9.3.1.1`、SolidWorks 2025 SP5.0。先验证可用的 Python 能导入 NumPy 和 OCP。已有局部依赖可通过 `--ocp-path` 指定。SolidWorks 默认由安装信息定位，也可用 `--sw-root`。依赖和网格排查见 [重建与排查](reconstruction.md)。

## 续接任务

首次运行会在 `--work-dir` 生成 `geometry.step`、`geometry.json` 和记录源 STL 哈希、单位及孔处理选项的 `mesh-request.json`。用相同的源与选项重跑可复用中间 STEP。变更单位、孔径或输入后请用新的工作目录。

- `--holes auto` 尝试恢复脚本支持的圆孔。 `--holes require` 适合明确必须恢复的可识别直通孔。 `--hole-diameter-mm` 只在原孔实测与指定直径吻合时采用。 `--holes keep` 保留源孔分面作为工作几何。若用户明确要求平滑孔或圆角，检查 `geometry.json` 与实际 B-Rep，继续重建仍有分面的指定位置。
- 若脚本在 STEP 导入处停止，从本机桌面打开该工作目录的 `geometry.step`，保存为 `imported.SLDPRT`，以相同参数加 `--imported-part imported.SLDPRT` 重跑。脚本在工作副本上断开 3D Interconnect 链接，并核对导入实体与 STEP 的外包尺寸和体积。不要把另一件形状相近的零件当作基线。
- 若 FeatureWorks 自动识别失败，可在 SolidWorks 中对独立导入体分步或交互识别。查看提示中具体会影响的配置表和子特征，在授权范围内处理工作副本。保存识别候选后以 `--recognized-part` 交给脚本完成约束和验收。
- 用户允许原生重建时，从工作 STEP 测量轮廓并写建模计划。加 `--plan plan.json --template part.prtdot` 重跑。每次原生尝试有自己的 `native-*` 子目录，包含独立基线、运行日志和验证预览。
- 如果模型已有经过实测验证的复杂曲面基线，或需要旋转、放样、钣金、多实体等超出这条脚本路线的特征，直接使用本技能的 SolidWorks 辅助脚本或原生 CAD 操作。保持源网格、曲面基线和交付零件之间可核验的几何对应。

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

辅助脚本 [solidworks-part.ps1](../scripts/solidworks/solidworks-part.ps1) 需由 Windows PowerShell 5.1 的 STA 模式执行。它支持 `Prepare`、`Recognize`、`Define`、`Rebuild`、`Audit` 和 `Validate`。 `Audit` 列出尺寸名、草图状态和实体信息。 `Validate` 重开候选文件，要求单一有效实体、完全定义且有驱动尺寸的草图和关联特征，检测剩余导入主体，并做几何基线的双向实体差。临时改动可以指定 `--edit-dimension 'D1@草图名'`。不指定时尝试代表性驱动尺寸并恢复原值。试改检查验证尺寸驱动实际形体，关键孔径、曲面和设计参数还应按用户要求单独核对。预览默认写到原生工作目录。

默认包围盒允许差 0.001 mm，体积及双向布尔差容差 0.01 mm³。先按源 STL 精度、真实几何变化及用户需求判断是否调整，记录依据。适用情况下核对最终孔轴、直径、深度、圆角半径和连接。回读通过后只交付最终 SLDPRT。
