export const UI_TEXT = {
  common: {
    refresh: '刷新',
    retry: '重试',
    unknownError: '未知错误',
    loadingFailed: '加载失败'
  },
  demo: {
    badge: '演示模式',
    statusReady: '演示数据已就绪',
    statusNotReady: '演示数据未就绪',
    bootstrap: '一键生成演示闭环数据',
    reset: '重置演示数据',
    switchToReal: '切到真实模式',
    switchToDemo: '切到演示模式',
    switchedToReal: '已切换到真实模式',
    switchedToDemo: '已切换到演示模式',
    modeNotice: '当前为演示模式：使用演示数据与半自动分发流程。'
  },
  layout: {
    appTitle: 'GEO 闭环优化助手',
    defaultTitle: '总览',
    apiKeyPlaceholder: '内部 API Key',
    saveKey: '保存',
    saveKeySuccess: '内部 API Key 已保存',
    menu: {
      overview: '总览',
      brands: '品牌档案',
      assets: '素材池',
      analysis: '分析中心',
      workshop: '内容工坊',
      distribution: '分发与反馈'
    }
  },
  overview: {
    cards: {
      brands: '品牌数',
      assets: '素材数',
      reports: '报告数',
      contents: '内容条目'
    },
    queue: {
      title: '任务状态',
      queued: '待发布',
      scheduled: '已排期',
      posted: '已发布',
      failed: '失败'
    },
    readiness: {
      title: '系统就绪状态',
      statusOk: '就绪',
      statusDegraded: '降级',
      unknown: '未知'
    },
    latestReports: '最新分析报告',
    latestInsights: '最新优化建议'
  },
  brands: {
    title: '品牌档案',
    create: '创建品牌',
    quickSave: '快速保存',
    table: {
      brand: '品牌',
      industry: '行业',
      tone: '语气',
      region: '区域',
      action: '操作'
    }
  },
  assets: {
    uploadTitle: '上传素材',
    pasteTitle: '粘贴文本素材',
    selectBrand: '选择品牌',
    uploadFile: '上传文件',
    saveText: '保存文本素材',
    listTitle: '素材列表'
  },
  analysis: {
    title: '运行 GEO 分析',
    run: '生成报告',
    reports: '分析报告',
    detail: '报告详情',
    agentTeam: '专家团队深度分析',
    agentTeamToggle: '启用专家团队（需 OpenRouter API Key）',
    agentTeamReport: '专家团队综合报告',
    modelLabel: '分析模型',
    modelDefault: '默认模型',
    modelClaude: 'Claude Sonnet 4.5（深度推理）',
    modelGemini: 'Gemini 2.5 Pro（数据分析）',
    geoVisibility: 'GEO 可见性得分'
  },
  workshop: {
    generateTitle: '从报告生成内容',
    listTitle: '内容工坊',
    generate: '生成内容',
    approve: '审核通过',
    exportMd: '导出 MD',
    exportPdf: '导出 PDF',
    wechatRichPost: '公众号一键图文（占位）',
    promptProfiles: '专家提示词档案',
    workflowSteps: 'Skill 子步骤编排',
    contentModelLabel: '内容生成模型',
    contentModelDefault: '默认模型',
    contentModelClaude: 'Claude Sonnet 4.5',
    contentModelGemini: 'Gemini 2.5 Pro'
  },
  distribution: {
    modeNotice:
      '当前为半自动发布模式：仅支持任务排队、人工发布、链接回填与状态流转。',
    createTitle: '创建发布任务（半自动）',
    queueTitle: '发布任务队列',
    performanceTitle: '效果数据录入',
    insightsTitle: '优化建议',
    createTask: '创建任务',
    savePerformance: '保存表现数据',
    runInsights: '生成优化建议',
    markPosted: '标记为已发布'
  }
}

export type UiText = typeof UI_TEXT
