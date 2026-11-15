window.__ModuleLoader__.load({
  id: 'dsh-stl-to-editable-part',
  factory(require) {
    const React = require('react')
    const h = React.createElement

    const NS = 'dsh-stl-to-editable-part'
    const PANEL_ID = 'stl-to-editable-part'

    const ZH = {
      navLabel: 'STL 转可编辑零件',
      eyebrow: 'DSH 技能 · 原生 CAD 工作流',
      title: 'STL 转可编辑 SolidWorks 零件',
      subtitle: '把 STL 网格重建为带原生特征、完全定义草图和驱动尺寸的 .SLDPRT。大平面可整面选取，能可靠恢复的孔使用解析几何。',
      badgePlane: '平面整面选取',
      badgeHole: '直通孔解析恢复',
      badgeNative: '原生特征树',
      routeTitle: '从网格到原生零件',
      routeHint: '自动路径优先，识别不足时从已验证的几何基线继续。',
      step1Title: '确认输入与比例',
      step1Body: '确认单位、左右件和交付位置。STL 本身不带单位，优先用已知尺寸校准。',
      step2Title: '重建解析几何',
      step2Body: '验证网格，合并共面三角面，恢复可可靠拟合的平面和直通圆孔。',
      step3Title: '生成原生特征',
      step3Body: '按实测方案建立 SolidWorks 原生特征。有验收记录时可快速重出同一零件。',
      step4Title: '校验后交付',
      step4Body: '保存、重开并强制重建，检查草图约束、驱动尺寸和下游特征。',
      noteTitle: '工作方式',
      noteBody: '每件使用独立工作目录。尺寸假设、采用的识别或重建路线，以及未恢复的几何都会写入交付说明。',
      launchTitle: '开始转换',
      launchHint: '填写 STL 路径，打开一个已填入任务的新会话。',
      pathLabel: 'STL 文件路径',
      pathPlaceholder: 'C:\\零件\\支架.stl',
      unitLabel: '单位',
      unitMm: '毫米 (mm)',
      unitCm: '厘米 (cm)',
      unitInch: '英寸 (in)',
      outputLabel: '输出文件名',
      optional: '可选',
      outputPlaceholder: '支架-可编辑.SLDPRT',
      outputDefault: '未指定（默认与源文件同目录，文件名加 -可编辑）',
      primaryAction: '打开转换会话',
      secondaryAction: '复制提示词',
      pathRequired: '请先填写 STL 文件路径。',
      copied: '提示词已复制。',
      copyFailed: '无法访问剪贴板，请手动选择提示词复制。',
      launched: '已在新会话中填入提示词，确认后发送。',
      unavailable: '当前界面无法打开会话，请直接在对话中调用该技能。',
      launchFailed: '打开会话失败，请直接在对话中调用该技能。',
      formHint: '提示词会包含路径、单位和交付要求；发送前仍可修改。',
      runtimeTitle: '运行环境',
      runtimeBody: 'Windows x64 · SolidWorks · Python 3.12 x64 · NumPy · OCP',
      scopeTitle: '适用范围',
      scopeBody: '适合单个闭合、定向流形网格。自动孔恢复限沿输入 Y 轴、两端可匹配的直通孔；复杂曲面、盲孔和圆角可能需要补充实测尺寸后重建。',
      manualHint: '也可以在对话中输入 /stl-to-editable-part 手动调用。',
      promptTemplate: `/stl-to-editable-part 请把下面的 STL 网格转换为可编辑的 SolidWorks 原生零件。

- STL 文件：{path}
- 单位：{unit}
- 输出文件：{output}

要求：先检查输入和依赖；恢复平面和可可靠拟合的直通圆孔，以拉伸、切除、孔等原生特征重建；完全定义建模草图，保留可修改的驱动尺寸；保存、重开并强制重建后再交付。请说明尺寸假设、采用的识别或重建路线，以及未恢复的几何。`,
    }

    const EN = {
      navLabel: 'STL to editable part',
      eyebrow: 'DSH SKILL · NATIVE CAD WORKFLOW',
      title: 'STL to editable SolidWorks part',
      subtitle: 'Rebuild STL meshes as .SLDPRT files with native features, fully defined sketches, and driving dimensions. Keep planar faces selectable as whole faces and recover reliable holes as analytic geometry.',
      badgePlane: 'Whole-face planes',
      badgeHole: 'Analytic through-holes',
      badgeNative: 'Native feature tree',
      routeTitle: 'From mesh to native part',
      routeHint: 'Try automation first, then continue from a verified geometry baseline when recognition falls short.',
      step1Title: 'Confirm input and scale',
      step1Body: 'Confirm units, handedness, and the delivery location. STL carries no units, so calibrate against a known dimension first.',
      step2Title: 'Rebuild analytic geometry',
      step2Body: 'Validate the mesh, merge coplanar triangles, and recover planes and reliably fitting through-holes.',
      step3Title: 'Create native features',
      step3Body: 'Build native SolidWorks features from a measured plan. Reuse a verified result for the same STL.',
      step4Title: 'Validate and deliver',
      step4Body: 'Save, reopen, and force a rebuild. Check sketch constraints, driving dimensions, and downstream features.',
      noteTitle: 'How it works',
      noteBody: 'Each part gets its own work directory. Dimensional assumptions, the recognition or reconstruction route, and any unrecovered geometry are recorded in the delivery notes.',
      launchTitle: 'Start a conversion',
      launchHint: 'Enter an STL path and open a new session with the task already drafted.',
      pathLabel: 'STL file path',
      pathPlaceholder: 'C:\\parts\\bracket.stl',
      unitLabel: 'Units',
      unitMm: 'Millimeters (mm)',
      unitCm: 'Centimeters (cm)',
      unitInch: 'Inches (in)',
      outputLabel: 'Output file',
      optional: 'Optional',
      outputPlaceholder: 'bracket-editable.SLDPRT',
      outputDefault: 'Not specified (defaults next to the source with an -editable suffix)',
      primaryAction: 'Open conversion session',
      secondaryAction: 'Copy prompt',
      pathRequired: 'Enter the STL file path first.',
      copied: 'Prompt copied.',
      copyFailed: 'Clipboard access is unavailable. Select the prompt and copy it manually.',
      launched: 'The prompt is drafted in a new session. Review it, then send.',
      unavailable: 'This interface cannot open a session here. Invoke the skill directly in a conversation.',
      launchFailed: 'Could not open a session. Invoke the skill directly in a conversation instead.',
      formHint: 'The prompt includes the path, units, and delivery requirements. You can still edit it before sending.',
      runtimeTitle: 'Runtime',
      runtimeBody: 'Windows x64 · SolidWorks · Python 3.12 x64 · NumPy · OCP',
      scopeTitle: 'Scope',
      scopeBody: 'Built for a single closed, oriented manifold mesh. Automatic hole recovery covers through-holes along the input Y axis with matchable ends. Complex surfaces, blind holes, and fillets may need measured dimensions first.',
      manualHint: 'You can also invoke /stl-to-editable-part directly in a conversation.',
      promptTemplate: `/stl-to-editable-part Convert the STL mesh below into an editable native SolidWorks part.

- STL file: {path}
- Units: {unit}
- Output file: {output}

Requirements: inspect the input and dependencies first; recover planar faces and any reliably fitting through-holes; rebuild with native extrude, cut, and hole features; fully define the modeling sketches and keep driving dimensions editable; save, reopen, and force a rebuild before delivery. Explain dimensional assumptions, the recognition or reconstruction route used, and any geometry not recovered.`,
    }

    const CSS = `
      .stl2p-root {
        box-sizing: border-box;
        min-height: 100%;
        overflow: auto;
        background: var(--dsw-alias-bg-base);
        color: var(--dsw-alias-label-primary);
      }
      .stl2p-root *, .stl2p-root *::before, .stl2p-root *::after { box-sizing: border-box; }
      .stl2p-shell {
        width: 100%;
        max-width: 1060px;
        margin: 0 auto;
        padding: 64px 44px 52px;
      }
      .stl2p-hero { display: flex; align-items: flex-start; gap: 20px; margin-bottom: 30px; }
      .stl2p-mark {
        flex: none;
        width: 64px;
        height: 64px;
        padding: 4px;
        border: 1px solid var(--dsw-alias-border-l1);
        border-radius: 16px;
        background: var(--dsw-alias-bg-layer-1);
      }
      .stl2p-mark svg { display: block; width: 100%; height: 100%; border-radius: 12px; }
      .stl2p-hero-copy { min-width: 0; padding-top: 3px; }
      .stl2p-eyebrow {
        margin: 0 0 7px;
        color: var(--dsw-alias-label-secondary);
        font-size: 11px;
        font-weight: 650;
        letter-spacing: .09em;
      }
      .stl2p-title {
        margin: 0;
        font-size: clamp(27px, 3.1vw, 35px);
        font-weight: 680;
        line-height: 1.18;
        letter-spacing: -.025em;
        text-wrap: balance;
      }
      .stl2p-subtitle {
        max-width: 760px;
        margin: 11px 0 0;
        color: var(--dsw-alias-label-secondary);
        font-size: 14.5px;
        line-height: 1.65;
        text-wrap: pretty;
      }
      .stl2p-badges { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
      .stl2p-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        min-height: 26px;
        padding: 3px 9px;
        border: 1px solid var(--dsw-alias-border-l1);
        border-radius: 999px;
        background: var(--dsw-alias-bg-layer-1);
        color: var(--dsw-alias-label-secondary);
        font-size: 11.5px;
        line-height: 1;
      }
      .stl2p-badge::before {
        width: 5px;
        height: 5px;
        border-radius: 50%;
        background: var(--dsw-alias-brand-primary);
        content: "";
      }
      .stl2p-grid {
        display: grid;
        grid-template-columns: minmax(0, 1.16fr) minmax(320px, .84fr);
        gap: 20px;
        align-items: start;
      }
      .stl2p-card {
        border: 1px solid var(--dsw-alias-border-l1);
        border-radius: 17px;
        background: var(--dsw-alias-bg-layer-1);
        padding: 24px;
      }
      .stl2p-launch {
        background: var(--dsw-alias-bg-layer-1);
        background: linear-gradient(180deg, color-mix(in srgb, var(--dsw-alias-brand-primary) 5%, var(--dsw-alias-bg-layer-1)) 0, var(--dsw-alias-bg-layer-1) 150px);
      }
      .stl2p-card-head { margin-bottom: 14px; }
      .stl2p-card-title {
        margin: 0;
        font-size: 17px;
        font-weight: 650;
        line-height: 1.35;
        letter-spacing: -.01em;
      }
      .stl2p-card-hint {
        margin: 6px 0 0;
        color: var(--dsw-alias-label-secondary);
        font-size: 12.5px;
        line-height: 1.55;
      }
      .stl2p-steps { margin: 0; padding: 0; list-style: none; }
      .stl2p-step {
        display: grid;
        grid-template-columns: 30px minmax(0, 1fr);
        gap: 13px;
        padding: 15px 0;
        border-top: 1px solid var(--dsw-alias-border-l1);
      }
      .stl2p-step:first-child { padding-top: 3px; border-top: 0; }
      .stl2p-step:last-child { padding-bottom: 3px; }
      .stl2p-step-num {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border: 1px solid color-mix(in srgb, var(--dsw-alias-brand-primary) 32%, var(--dsw-alias-border-l1));
        border-radius: 50%;
        background: color-mix(in srgb, var(--dsw-alias-brand-primary) 9%, var(--dsw-alias-bg-layer-1));
        color: var(--dsw-alias-brand-primary);
        font-size: 11.5px;
        font-weight: 700;
        font-variant-numeric: tabular-nums;
      }
      .stl2p-step-title { margin: 2px 0 3px; font-size: 13.5px; font-weight: 650; line-height: 1.45; }
      .stl2p-step-body { margin: 0; color: var(--dsw-alias-label-secondary); font-size: 12.5px; line-height: 1.6; }
      .stl2p-note {
        margin-top: 17px;
        padding: 13px 15px;
        border-left: 2px solid var(--dsw-alias-brand-primary);
        border-radius: 0 10px 10px 0;
        background: var(--dsw-alias-bg-layer-2);
      }
      .stl2p-note-title { display: block; margin-bottom: 4px; font-size: 12px; font-weight: 650; }
      .stl2p-note-body { margin: 0; color: var(--dsw-alias-label-secondary); font-size: 12px; line-height: 1.6; }
      .stl2p-form { display: flex; flex-direction: column; gap: 14px; }
      .stl2p-field { display: flex; flex-direction: column; gap: 7px; min-width: 0; }
      .stl2p-label-row { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
      .stl2p-label { font-size: 12.5px; font-weight: 650; }
      .stl2p-optional { color: var(--dsw-alias-label-secondary); font-size: 11px; font-weight: 500; }
      .stl2p-input, .stl2p-select {
        width: 100%;
        min-height: 41px;
        padding: 0 11px;
        border: 1px solid var(--dsw-alias-border-l1);
        border-radius: 9px;
        outline: none;
        background: var(--dsw-alias-bg-base);
        color: var(--dsw-alias-label-primary);
        font: inherit;
        font-size: 13px;
      }
      .stl2p-input::placeholder { color: var(--dsw-alias-state-idle-primary); }
      .stl2p-input:focus, .stl2p-select:focus {
        border-color: var(--dsw-alias-brand-primary);
        box-shadow: 0 0 0 3px color-mix(in srgb, var(--dsw-alias-brand-primary) 18%, transparent);
      }
      .stl2p-row { display: grid; grid-template-columns: 122px minmax(0, 1fr); gap: 10px; }
      .stl2p-actions { display: flex; flex-direction: column; gap: 8px; margin-top: 2px; }
      .stl2p-button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 7px;
        width: 100%;
        min-height: 42px;
        padding: 0 15px;
        border-radius: 9px;
        font: inherit;
        font-size: 13px;
        font-weight: 650;
        line-height: 1;
        cursor: pointer;
      }
      .stl2p-button--primary {
        border: 1px solid var(--dsw-alias-brand-primary);
        background: var(--dsw-alias-brand-primary);
        color: var(--dsw-alias-bg-base);
      }
      .stl2p-button--primary:hover { filter: brightness(1.07); }
      .stl2p-button--secondary {
        border: 1px solid var(--dsw-alias-border-l1);
        background: var(--dsw-alias-bg-layer-2);
        color: var(--dsw-alias-label-primary);
      }
      .stl2p-button--secondary:hover {
        border-color: var(--dsw-alias-border-l2);
        background: color-mix(in srgb, var(--dsw-alias-label-primary) 4%, var(--dsw-alias-bg-layer-2));
      }
      .stl2p-button:focus-visible { outline: 2px solid var(--dsw-alias-brand-primary); outline-offset: 2px; }
      .stl2p-button svg { display: block; flex: none; }
      .stl2p-form-hint { margin: -2px 0 0; color: var(--dsw-alias-label-secondary); font-size: 11.5px; line-height: 1.55; }
      .stl2p-feedback {
        margin: 0;
        padding: 9px 11px;
        border: 1px solid var(--dsw-alias-border-l1);
        border-radius: 8px;
        font-size: 12px;
        line-height: 1.5;
      }
      .stl2p-feedback--success {
        border-color: color-mix(in srgb, var(--dsw-alias-state-success-primary) 38%, var(--dsw-alias-border-l1));
        background: color-mix(in srgb, var(--dsw-alias-state-success-primary) 9%, var(--dsw-alias-bg-layer-1));
        color: var(--dsw-alias-state-success-primary);
      }
      .stl2p-feedback--error {
        border-color: color-mix(in srgb, var(--dsw-alias-state-error-primary) 38%, var(--dsw-alias-border-l1));
        background: color-mix(in srgb, var(--dsw-alias-state-error-primary) 9%, var(--dsw-alias-bg-layer-1));
        color: var(--dsw-alias-state-error-primary);
      }
      .stl2p-runtime {
        margin-top: 20px;
        padding-top: 16px;
        border-top: 1px solid var(--dsw-alias-border-l1);
      }
      .stl2p-runtime-title, .stl2p-scope-title {
        margin: 0 0 4px;
        color: var(--dsw-alias-label-secondary);
        font-size: 10.5px;
        font-weight: 700;
        letter-spacing: .06em;
        text-transform: uppercase;
      }
      .stl2p-runtime-body { margin: 0; color: var(--dsw-alias-label-secondary); font-size: 11.5px; line-height: 1.55; }
      .stl2p-footer {
        margin-top: 22px;
        padding-top: 18px;
        border-top: 1px solid var(--dsw-alias-border-l1);
      }
      .stl2p-scope-body { margin: 0; color: var(--dsw-alias-label-secondary); font-size: 12px; line-height: 1.65; }
      .stl2p-manual { margin: 9px 0 0; color: var(--dsw-alias-label-secondary); font-size: 12px; line-height: 1.6; }
      .stl2p-manual code {
        padding: 1px 5px;
        border: 1px solid var(--dsw-alias-border-l1);
        border-radius: 5px;
        background: var(--dsw-alias-bg-layer-2);
        color: var(--dsw-alias-label-primary);
        font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
        font-size: 11px;
      }
      @media (max-width: 920px) {
        .stl2p-shell { padding: 52px 28px 42px; }
        .stl2p-grid { grid-template-columns: minmax(0, 1fr); }
      }
      @media (max-width: 620px) {
        .stl2p-shell { padding: 42px 18px 36px; }
        .stl2p-hero { gap: 14px; }
        .stl2p-mark { width: 50px; height: 50px; border-radius: 13px; }
        .stl2p-title { font-size: 25px; }
        .stl2p-card { padding: 19px; border-radius: 14px; }
        .stl2p-row { grid-template-columns: minmax(0, 1fr); }
      }
    `

    function PluginMark() {
      return h(
        'svg',
        { viewBox: '0 0 64 64', role: 'img', 'aria-hidden': 'true', focusable: 'false' },
        h('rect', { x: '2', y: '2', width: '60', height: '60', rx: '14', fill: '#103b4f' }),
        h('path', { d: 'M13 27 36 14l15 10-23 14z', fill: '#8bded2' }),
        h('path', { d: 'm13 27 15 11v13L13 40z', fill: '#4498a1' }),
        h('path', { d: 'm28 38 23-14v13L28 51z', fill: '#57b5b4' }),
        h('path', {
          d: 'm19 24 15 11m-6-16 15 10m-30-2 38-3',
          fill: 'none',
          stroke: '#277481',
          strokeWidth: '1.25',
        }),
        h('ellipse', {
          cx: '39',
          cy: '37',
          rx: '5.5',
          ry: '3.8',
          transform: 'rotate(-31 39 37)',
          fill: '#103b4f',
        }),
      )
    }

    function SidebarIcon(props) {
      const size = props && typeof props.size === 'number' ? props.size : 18
      return h(
        'svg',
        {
          width: size,
          height: size,
          viewBox: '0 0 24 24',
          fill: 'none',
          'aria-hidden': 'true',
          focusable: 'false',
          style: { display: 'block' },
        },
        h('path', {
          d: 'M12 2.9 20.4 8v8L12 21.1 3.6 16V8L12 2.9Z',
          stroke: 'currentColor',
          strokeWidth: '1.55',
          strokeLinejoin: 'round',
        }),
        h('path', {
          d: 'm4 8.2 8 4.7 8-4.7M12 12.9v7.7',
          stroke: 'currentColor',
          strokeWidth: '1.55',
          strokeLinejoin: 'round',
        }),
        h('ellipse', {
          cx: '15.1',
          cy: '11.1',
          rx: '2.2',
          ry: '1.45',
          transform: 'rotate(-28 15.1 11.1)',
          stroke: 'currentColor',
          strokeWidth: '1.35',
        }),
      )
    }

    function ArrowIcon() {
      return h(
        'svg',
        { width: '15', height: '15', viewBox: '0 0 16 16', fill: 'none', 'aria-hidden': 'true' },
        h('path', {
          d: 'M3.25 8h9.5M8.75 4l4 4-4 4',
          stroke: 'currentColor',
          strokeWidth: '1.5',
          strokeLinecap: 'round',
          strokeLinejoin: 'round',
        }),
      )
    }

    return {
      inject: ['slots', 'locale'],
      apply(ctx) {
        const t = ctx.locale.bind(NS)

        ctx.effect(() => {
          const disposers = [
            ctx.locale.register(NS, 'zh-CN', ZH),
            ctx.locale.register(NS, 'zh', ZH),
            ctx.locale.register(NS, 'en', EN),
            ctx.locale.register(NS, 'en-US', EN),
          ]
          return () => {
            for (const dispose of disposers) dispose()
          }
        })

        function MainPanel() {
          const [path, setPath] = React.useState('')
          const [unit, setUnit] = React.useState('mm')
          const [output, setOutput] = React.useState('')
          const [feedback, setFeedback] = React.useState(null)
          const [, setLocaleRevision] = React.useState(0)

          React.useEffect(() => ctx.locale.subscribe(() => {
            setLocaleRevision((revision) => revision + 1)
          }), [])

          const unitOptions = [
            { value: 'mm', label: t('unitMm') },
            { value: 'cm', label: t('unitCm') },
            { value: 'in', label: t('unitInch') },
          ]
          const unitLabel = (unitOptions.find((option) => option.value === unit) || unitOptions[0]).label

          function buildPrompt() {
            const target = output.trim() || t('outputDefault')
            return t('promptTemplate')
              .replace(/\{path\}/g, () => path.trim())
              .replace(/\{unit\}/g, () => unitLabel)
              .replace(/\{output\}/g, () => target)
          }

          function requirePath() {
            if (path.trim()) return true
            setFeedback({ kind: 'error', text: t('pathRequired') })
            return false
          }

          function openSession() {
            if (!requirePath()) return
            const workspace = ctx.get('uiWorkspace')
            if (!workspace || typeof workspace.startSession !== 'function') {
              setFeedback({ kind: 'error', text: t('unavailable') })
              return
            }
            try {
              workspace.startSession(undefined, {
                prompt: buildPrompt(),
                whenDraftExists: 'append',
              })
              setFeedback({ kind: 'success', text: t('launched') })
            } catch (error) {
              console.error('[dsh-stl-to-editable-part] failed to open a session', error)
              setFeedback({ kind: 'error', text: t('launchFailed') })
            }
          }

          async function copyPrompt() {
            if (!requirePath()) return
            try {
              if (!navigator.clipboard || typeof navigator.clipboard.writeText !== 'function') {
                throw new Error('Clipboard API unavailable')
              }
              await navigator.clipboard.writeText(buildPrompt())
              setFeedback({ kind: 'success', text: t('copied') })
            } catch (error) {
              console.error('[dsh-stl-to-editable-part] failed to copy the prompt', error)
              setFeedback({ kind: 'error', text: t('copyFailed') })
            }
          }

          const badges = ['badgePlane', 'badgeHole', 'badgeNative']
          const steps = [
            ['step1Title', 'step1Body'],
            ['step2Title', 'step2Body'],
            ['step3Title', 'step3Body'],
            ['step4Title', 'step4Body'],
          ]

          return h(
            'div',
            { className: 'stl2p-root' },
            h('style', null, CSS),
            h(
              'div',
              { className: 'stl2p-shell' },
              h(
                'header',
                { className: 'stl2p-hero' },
                h('div', { className: 'stl2p-mark' }, h(PluginMark)),
                h(
                  'div',
                  { className: 'stl2p-hero-copy' },
                  h('p', { className: 'stl2p-eyebrow' }, t('eyebrow')),
                  h('h1', { className: 'stl2p-title' }, t('title')),
                  h('p', { className: 'stl2p-subtitle' }, t('subtitle')),
                  h(
                    'div',
                    { className: 'stl2p-badges' },
                    badges.map((key) => h('span', { className: 'stl2p-badge', key }, t(key))),
                  ),
                ),
              ),
              h(
                'div',
                { className: 'stl2p-grid' },
                h(
                  'section',
                  { className: 'stl2p-card', 'aria-labelledby': 'stl2p-route-title' },
                  h(
                    'div',
                    { className: 'stl2p-card-head' },
                    h('h2', { className: 'stl2p-card-title', id: 'stl2p-route-title' }, t('routeTitle')),
                    h('p', { className: 'stl2p-card-hint' }, t('routeHint')),
                  ),
                  h(
                    'ol',
                    { className: 'stl2p-steps' },
                    steps.map(([titleKey, bodyKey], index) => h(
                      'li',
                      { className: 'stl2p-step', key: titleKey },
                      h('span', { className: 'stl2p-step-num', 'aria-hidden': 'true' }, String(index + 1).padStart(2, '0')),
                      h(
                        'div',
                        null,
                        h('h3', { className: 'stl2p-step-title' }, t(titleKey)),
                        h('p', { className: 'stl2p-step-body' }, t(bodyKey)),
                      ),
                    )),
                  ),
                  h(
                    'div',
                    { className: 'stl2p-note' },
                    h('strong', { className: 'stl2p-note-title' }, t('noteTitle')),
                    h('p', { className: 'stl2p-note-body' }, t('noteBody')),
                  ),
                ),
                h(
                  'section',
                  { className: 'stl2p-card stl2p-launch', 'aria-labelledby': 'stl2p-launch-title' },
                  h(
                    'div',
                    { className: 'stl2p-card-head' },
                    h('h2', { className: 'stl2p-card-title', id: 'stl2p-launch-title' }, t('launchTitle')),
                    h('p', { className: 'stl2p-card-hint' }, t('launchHint')),
                  ),
                  h(
                    'form',
                    {
                      className: 'stl2p-form',
                      onSubmit: (event) => {
                        event.preventDefault()
                        openSession()
                      },
                    },
                    h(
                      'div',
                      { className: 'stl2p-field' },
                      h('label', { className: 'stl2p-label', htmlFor: 'stl2p-path' }, t('pathLabel')),
                      h('input', {
                        id: 'stl2p-path',
                        className: 'stl2p-input',
                        type: 'text',
                        value: path,
                        placeholder: t('pathPlaceholder'),
                        spellCheck: false,
                        autoComplete: 'off',
                        onChange: (event) => {
                          setPath(event.target.value)
                          if (feedback && feedback.kind === 'error') setFeedback(null)
                        },
                      }),
                    ),
                    h(
                      'div',
                      { className: 'stl2p-row' },
                      h(
                        'div',
                        { className: 'stl2p-field' },
                        h('label', { className: 'stl2p-label', htmlFor: 'stl2p-unit' }, t('unitLabel')),
                        h(
                          'select',
                          {
                            id: 'stl2p-unit',
                            className: 'stl2p-select',
                            value: unit,
                            onChange: (event) => setUnit(event.target.value),
                          },
                          unitOptions.map((option) => h('option', { key: option.value, value: option.value }, option.label)),
                        ),
                      ),
                      h(
                        'div',
                        { className: 'stl2p-field' },
                        h(
                          'div',
                          { className: 'stl2p-label-row' },
                          h('label', { className: 'stl2p-label', htmlFor: 'stl2p-output' }, t('outputLabel')),
                          h('span', { className: 'stl2p-optional' }, t('optional')),
                        ),
                        h('input', {
                          id: 'stl2p-output',
                          className: 'stl2p-input',
                          type: 'text',
                          value: output,
                          placeholder: t('outputPlaceholder'),
                          spellCheck: false,
                          autoComplete: 'off',
                          onChange: (event) => setOutput(event.target.value),
                        }),
                      ),
                    ),
                    h(
                      'div',
                      { className: 'stl2p-actions' },
                      h(
                        'button',
                        { className: 'stl2p-button stl2p-button--primary', type: 'submit' },
                        h(ArrowIcon),
                        t('primaryAction'),
                      ),
                      h(
                        'button',
                        {
                          className: 'stl2p-button stl2p-button--secondary',
                          type: 'button',
                          onClick: copyPrompt,
                        },
                        t('secondaryAction'),
                      ),
                    ),
                    feedback && h(
                      'p',
                      {
                        className: `stl2p-feedback stl2p-feedback--${feedback.kind}`,
                        role: feedback.kind === 'error' ? 'alert' : 'status',
                        'aria-live': 'polite',
                      },
                      feedback.text,
                    ),
                    h('p', { className: 'stl2p-form-hint' }, t('formHint')),
                  ),
                  h(
                    'div',
                    { className: 'stl2p-runtime' },
                    h('h3', { className: 'stl2p-runtime-title' }, t('runtimeTitle')),
                    h('p', { className: 'stl2p-runtime-body' }, t('runtimeBody')),
                  ),
                ),
              ),
              h(
                'footer',
                { className: 'stl2p-footer' },
                h('h2', { className: 'stl2p-scope-title' }, t('scopeTitle')),
                h('p', { className: 'stl2p-scope-body' }, t('scopeBody')),
                h(
                  'p',
                  { className: 'stl2p-manual' },
                  t('manualHint').split('/stl-to-editable-part').map((part, index, parts) => (
                    index < parts.length - 1
                      ? h(React.Fragment, { key: index }, part, h('code', null, '/stl-to-editable-part'))
                      : h(React.Fragment, { key: index }, part)
                  )),
                ),
              ),
            ),
          )
        }

        ctx.slots.inject('main', () => ctx.slots.register({
          name: 'main',
          key: PANEL_ID,
        }, MainPanel))

        ctx.slots.inject('sidebar.panellist', () => ctx.slots.register({
          name: 'sidebar.panellist',
          id: PANEL_ID,
          order: 20,
          label: () => t('navLabel'),
        }, SidebarIcon))
      },
    }
  },
})
