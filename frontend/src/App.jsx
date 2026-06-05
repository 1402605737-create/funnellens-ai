import { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  BadgeCheck,
  BarChart3,
  Bot,
  ClipboardCheck,
  FileSearch,
  FlaskConical,
  Gauge,
  Link2,
  Loader2,
  Plus,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Target,
  Wand2,
} from 'lucide-react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

const defaultMetrics = `日期,展示量,点击量,转化数,花费,收入
2026-05-27,18400,680,9,742.5,891
2026-05-28,19250,731,10,781.2,990
2026-05-29,17610,602,7,694.8,693
2026-05-30,20120,774,12,823.3,1188
2026-05-31,21600,833,13,862,1287
2026-06-01,23100,884,14,902.4,1386
2026-06-02,22680,861,11,881.1,1089`;

const tabConfig = [
  { key: 'audit', icon: Gauge },
  { key: 'claims', icon: Target },
  { key: 'trace', icon: Bot },
  { key: 'evidence', icon: ShieldCheck },
  { key: 'experiments', icon: FlaskConical },
  { key: 'metrics', icon: BarChart3 },
];

const copyBook = {
  zh: {
    subtitle: '中文增长投放诊断 Agent',
    runAudit: '运行诊断',
    auditing: '诊断中',
    createDemo: '载入中文广告样例',
    campaigns: '广告项目',
    noCampaigns: '暂无广告项目',
    newAudit: '新建诊断',
    create: '创建项目',
    eyebrow: '广告素材 × 落地页',
    workspaceTitle: '广告转化诊断工作台',
    noBrand: '未选择品牌',
    readyTitle: '准备开始广告漏斗诊断',
    readyBody: '创建一个中文广告项目，或载入内置样例。',
    creative: '广告素材',
    landingSnapshot: '落地页快照',
    snapshotPending: '运行诊断后，系统会抓取落地页并保存证据。',
    source: '来源',
    diagnosis: '诊断结论',
    noDiagnosis: '运行诊断后生成转化问题分析。',
    fallback: '本地规则',
    deepseek: 'DeepSeek',
    confidence: '置信度',
    mappingPending: '等待匹配。',
    noClaims: '还没有分析广告承诺。',
    noTrace: '运行诊断后展示 Agent 执行轨迹。',
    noEvidence: '证据库暂无内容。',
    noExperiments: '运行诊断后生成实验方案。',
    experimentBoard: '实验看板',
    recommendations: '优化建议',
    effort: '成本',
    review: '人工确认',
    languageZh: '中文',
    languageEn: 'EN',
    form: {
      brand: '品牌',
      campaign: '广告项目',
      category: '产品类别',
      landingUrl: '落地页 URL',
      adCopy: '广告文案',
      metricsCsv: '投放数据 CSV',
    },
    tabs: {
      audit: '诊断',
      claims: '承诺映射',
      trace: 'Agent 轨迹',
      evidence: '证据库',
      experiments: '实验方案',
      metrics: '指标',
    },
    scores: {
      message_match: '承诺承接',
      cta_friction: 'CTA 阻力',
      trust_proof: '可信证据',
      mobile_readiness: '移动端质量',
      experiment_priority: '实验优先级',
    },
    status: {
      ready: '就绪',
      draft: '草稿',
      running: '运行中',
      analyzed: '已分析',
      completed: '已完成',
      success: '成功',
      warning: '需关注',
      proposed: '待评审',
    },
    mapping: {
      matched: '已承接',
      weak_match: '弱承接',
      missing: '缺失',
      conflict: '冲突',
      pending: '待分析',
    },
    claimType: {
      hook: '钩子',
      benefit: '卖点',
      offer: '优惠',
      audience: '人群',
      time: '时效',
      proof: '证据',
      cta: '行动',
    },
    sourceType: {
      landing_page: '落地页证据',
      missing_evidence: '缺失证据',
      crawler_error: '抓取异常',
    },
    priority: {
      high: '高',
      medium: '中',
      low: '低',
    },
    effortValue: {
      high: '高',
      medium: '中',
      low: '低',
    },
  },
  en: {
    subtitle: 'Growth audit agent',
    runAudit: 'Run Audit',
    auditing: 'Auditing',
    createDemo: 'Load demo campaign',
    campaigns: 'Campaigns',
    noCampaigns: 'No campaigns yet.',
    newAudit: 'New Audit',
    create: 'Create',
    eyebrow: 'Ad creative × landing page',
    workspaceTitle: 'Funnel audit workspace',
    noBrand: 'No brand selected',
    readyTitle: 'Ready for a funnel audit',
    readyBody: 'Create a campaign or load the demo dataset.',
    creative: 'Creative',
    landingSnapshot: 'Landing Snapshot',
    snapshotPending: 'Run the audit to crawl the landing page and store page evidence.',
    source: 'source',
    diagnosis: 'Diagnosis',
    noDiagnosis: 'Run the audit to generate a conversion diagnosis.',
    fallback: 'fallback',
    deepseek: 'DeepSeek',
    confidence: 'confidence',
    mappingPending: 'Mapping pending.',
    noClaims: 'No claims analyzed yet.',
    noTrace: 'Agent trace will appear after an audit.',
    noEvidence: 'Evidence vault is empty.',
    noExperiments: 'Experiment briefs will appear after an audit.',
    experimentBoard: 'Experiment Board',
    recommendations: 'Recommendations',
    effort: 'effort',
    review: 'review',
    languageZh: '中文',
    languageEn: 'EN',
    form: {
      brand: 'Brand',
      campaign: 'Campaign',
      category: 'Category',
      landingUrl: 'Landing URL',
      adCopy: 'Ad Copy',
      metricsCsv: 'Metrics CSV',
    },
    tabs: {
      audit: 'Audit',
      claims: 'Claims',
      trace: 'Trace',
      evidence: 'Evidence',
      experiments: 'Experiments',
      metrics: 'Metrics',
    },
    scores: {
      message_match: 'Message Match',
      cta_friction: 'CTA Friction',
      trust_proof: 'Trust Proof',
      mobile_readiness: 'Mobile Readiness',
      experiment_priority: 'Experiment Priority',
    },
    status: {
      ready: 'ready',
      draft: 'draft',
      running: 'running',
      analyzed: 'analyzed',
      completed: 'completed',
      success: 'success',
      warning: 'warning',
      proposed: 'proposed',
    },
    mapping: {
      matched: 'matched',
      weak_match: 'weak match',
      missing: 'missing',
      conflict: 'conflict',
      pending: 'pending',
    },
    claimType: {
      hook: 'hook',
      benefit: 'benefit',
      offer: 'offer',
      audience: 'audience',
      time: 'time',
      proof: 'proof',
      cta: 'cta',
    },
    sourceType: {
      landing_page: 'landing page',
      missing_evidence: 'missing evidence',
      crawler_error: 'crawler error',
    },
    priority: {
      high: 'high',
      medium: 'medium',
      low: 'low',
    },
    effortValue: {
      high: 'high',
      medium: 'medium',
      low: 'low',
    },
  },
};

function App() {
  const [locale, setLocale] = useState(() => localStorage.getItem('funnellens_locale') || 'zh');
  const copy = copyBook[locale] || copyBook.zh;
  const [campaigns, setCampaigns] = useState([]);
  const [campaign, setCampaign] = useState(null);
  const [activeTab, setActiveTab] = useState('audit');
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    brand_name: '云栈 DevBox',
    campaign_name: '中文开发者工具免费试用投放',
    product_category: '中文开发者工具 / AI 应用后端',
    goal: 'signup',
    target_audience: '中文独立开发者、AI 应用创业团队、增长工程师',
    primary_kpi: 'CVR',
    landing_page_url: `${API_BASE}/demo-landing/chinese-devtool-ad`,
    ad_text:
      '10 分钟搭好 AI 应用后端。\n专为中文开发者和独立产品团队设计。\n7 天免费试用，无需信用卡。\n用一套模板把部署成本降低 30%。',
    metrics_csv: defaultMetrics,
  });

  useEffect(() => {
    boot();
  }, []);

  useEffect(() => {
    localStorage.setItem('funnellens_locale', locale);
  }, [locale]);

  async function boot() {
    setLoading(true);
    setError('');
    try {
      const list = await api('/api/campaigns');
      setCampaigns(list);
      if (list.length) {
        await loadCampaign(list[0].id);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadCampaign(id) {
    const detail = await api(`/api/campaigns/${id}`);
    setCampaign(detail);
  }

  async function createDemo() {
    setLoading(true);
    setError('');
    try {
      const detail = await api('/api/demo', { method: 'POST' });
      setCampaign(detail);
      await boot();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function createCampaign(event) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const payload = {
        ...form,
        metrics: parseMetricsCsv(form.metrics_csv),
      };
      delete payload.metrics_csv;
      const detail = await api('/api/campaigns', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      setCampaign(detail);
      await boot();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function runAudit() {
    if (!campaign) return;
    setAnalyzing(true);
    setError('');
    try {
      const detail = await api(`/api/campaigns/${campaign.id}/analyze`, {
        method: 'POST',
        body: JSON.stringify({ locale: locale === 'zh' ? 'zh-CN' : 'en-US' }),
      });
      setCampaign(detail);
      setActiveTab('audit');
    } catch (err) {
      setError(err.message);
    } finally {
      setAnalyzing(false);
    }
  }

  const currentTask = campaign?.agent_tasks?.[0];
  const metricRows = useMemo(() => buildMetricRows(campaign?.metrics || []), [campaign]);
  const firstPage = campaign?.landing_pages?.[0];
  const latestSnapshot = firstPage?.snapshots?.[0];
  const adText = campaign?.ad_assets?.[0]?.content || '';

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <div className="brand-mark">
            <Sparkles size={22} />
          </div>
          <div>
            <h1>FunnelLens AI</h1>
            <p>{copy.subtitle}</p>
          </div>
        </div>

        <div className="language-toggle" aria-label="language switch">
          <button className={locale === 'zh' ? 'active' : ''} onClick={() => setLocale('zh')} type="button">
            {copy.languageZh}
          </button>
          <button className={locale === 'en' ? 'active' : ''} onClick={() => setLocale('en')} type="button">
            {copy.languageEn}
          </button>
        </div>

        <div className="side-actions">
          <button className="primary-action" onClick={runAudit} disabled={!campaign || analyzing} title={copy.runAudit}>
            {analyzing ? <Loader2 className="spin" size={18} /> : <Wand2 size={18} />}
            <span>{analyzing ? copy.auditing : copy.runAudit}</span>
          </button>
          <button className="icon-action" onClick={createDemo} disabled={loading} title={copy.createDemo}>
            <RefreshCw size={17} />
          </button>
        </div>

        <section className="campaign-list">
          <div className="section-label">{copy.campaigns}</div>
          {campaigns.length === 0 && <p className="empty-text">{copy.noCampaigns}</p>}
          {campaigns.map((item) => (
            <button
              key={item.id}
              className={`campaign-row ${campaign?.id === item.id ? 'active' : ''}`}
              onClick={() => loadCampaign(item.id)}
            >
              <span>{item.name}</span>
              <small>{item.brand}</small>
            </button>
          ))}
        </section>

        <form className="create-panel" onSubmit={createCampaign}>
          <div className="section-label">{copy.newAudit}</div>
          <Input label={copy.form.brand} value={form.brand_name} onChange={(value) => setForm({ ...form, brand_name: value })} />
          <Input label={copy.form.campaign} value={form.campaign_name} onChange={(value) => setForm({ ...form, campaign_name: value })} />
          <Input label={copy.form.category} value={form.product_category} onChange={(value) => setForm({ ...form, product_category: value })} />
          <Input label={copy.form.landingUrl} value={form.landing_page_url} onChange={(value) => setForm({ ...form, landing_page_url: value })} />
          <label className="field">
            <span>{copy.form.adCopy}</span>
            <textarea
              value={form.ad_text}
              onChange={(event) => setForm({ ...form, ad_text: event.target.value })}
              rows={5}
            />
          </label>
          <label className="field">
            <span>{copy.form.metricsCsv}</span>
            <textarea
              value={form.metrics_csv}
              onChange={(event) => setForm({ ...form, metrics_csv: event.target.value })}
              rows={6}
            />
          </label>
          <button className="secondary-action" type="submit" disabled={loading} title={copy.create}>
            <Plus size={17} />
            <span>{copy.create}</span>
          </button>
        </form>
      </aside>

      <main className="main-surface">
        <header className="topbar">
          <div>
            <p className="eyebrow">{copy.eyebrow}</p>
            <h2>{campaign?.name || copy.workspaceTitle}</h2>
          </div>
          <div className="status-strip">
            <Badge status={campaign?.status || 'ready'} copy={copy} />
            <span>{campaign?.brand || copy.noBrand}</span>
          </div>
        </header>

        {error && <div className="error-banner">{error}</div>}

        {campaign ? (
          <>
            <section className="score-band">
              <ScoreCard label={copy.scores.message_match} value={campaign.scores.message_match} icon={Target} tone="good" />
              <ScoreCard label={copy.scores.cta_friction} value={campaign.scores.cta_friction} icon={Activity} tone="risk" />
              <ScoreCard label={copy.scores.trust_proof} value={campaign.scores.trust_proof} icon={ShieldCheck} tone="good" />
              <ScoreCard label={copy.scores.experiment_priority} value={campaign.scores.experiment_priority} icon={FlaskConical} tone="focus" />
            </section>

            <section className="overview-band">
              <div className="creative-preview">
                <div className="section-label">{copy.creative}</div>
                <p>{adText}</p>
              </div>
              <div className="landing-preview">
                <div className="section-label">{copy.landingSnapshot}</div>
                <h3>{latestSnapshot?.title || firstPage?.url || copy.snapshotPending}</h3>
                <p>{latestSnapshot?.text_excerpt || copy.snapshotPending}</p>
                {latestSnapshot?.final_url && (
                  <a href={latestSnapshot.final_url} target="_blank" rel="noreferrer">
                    <Link2 size={15} />
                    <span>{latestSnapshot.final_url}</span>
                  </a>
                )}
              </div>
            </section>

            <nav className="tabs" aria-label="Analysis views">
              {tabConfig.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.key}
                    className={activeTab === tab.key ? 'active' : ''}
                    onClick={() => setActiveTab(tab.key)}
                    title={copy.tabs[tab.key]}
                  >
                    <Icon size={17} />
                    <span>{copy.tabs[tab.key]}</span>
                  </button>
                );
              })}
            </nav>

            <section className="workspace-panel">
              {activeTab === 'audit' && <AuditView campaign={campaign} copy={copy} />}
              {activeTab === 'claims' && <ClaimsView claims={campaign.claims} copy={copy} />}
              {activeTab === 'trace' && <TraceView task={currentTask} copy={copy} />}
              {activeTab === 'evidence' && <EvidenceView items={campaign.evidence_items} copy={copy} />}
              {activeTab === 'experiments' && <ExperimentsView experiments={campaign.experiments} recommendations={campaign.recommendations} copy={copy} />}
              {activeTab === 'metrics' && <MetricsView rows={metricRows} summary={campaign.metrics_summary} />}
            </section>
          </>
        ) : (
          <section className="empty-state">
            <FileSearch size={28} />
            <h3>{copy.readyTitle}</h3>
            <p>{copy.readyBody}</p>
            <button className="primary-action" onClick={createDemo}>
              <RefreshCw size={17} />
              <span>{copy.createDemo}</span>
            </button>
          </section>
        )}
      </main>
    </div>
  );
}

function Input({ label, value, onChange }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function ScoreCard({ label, value, icon: Icon, tone }) {
  const numeric = Math.round(Number(value || 0));
  return (
    <div className={`score-card ${tone}`}>
      <div className="score-icon">
        <Icon size={18} />
      </div>
      <div>
        <span>{label}</span>
        <strong>{numeric}</strong>
      </div>
    </div>
  );
}

function Badge({ status, copy }) {
  return <span className={`badge ${status}`}>{copy.status[status] || status}</span>;
}

function AuditView({ campaign, copy }) {
  const hasDiagnosis = Boolean(campaign.diagnosis);
  const latestRun = campaign.ai_runs?.[0];
  return (
    <div className="audit-grid">
      <div className="diagnosis-panel">
        <div className="panel-title">
          <ClipboardCheck size={18} />
          <h3>{copy.diagnosis}</h3>
        </div>
        <p>{hasDiagnosis ? campaign.diagnosis : copy.noDiagnosis}</p>
        {latestRun && (
          <div className="run-meta">
            <span>{latestRun.model}</span>
            <span>{latestRun.used_fallback ? copy.fallback : copy.deepseek}</span>
          </div>
        )}
      </div>
      <div className="score-matrix">
        {Object.entries(campaign.scores).map(([key, value]) => (
          <div key={key} className="matrix-row">
            <span>{copy.scores[key] || labelize(key)}</span>
            <div className="bar-track">
              <div style={{ width: `${Math.min(100, Math.max(0, value || 0))}%` }} />
            </div>
            <strong>{Math.round(value || 0)}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function ClaimsView({ claims, copy }) {
  if (!claims?.length) return <EmptyPanel icon={Target} text={copy.noClaims} />;
  return (
    <div className="claim-list">
      {claims.map((claim) => {
        const mapping = claim.mappings?.[0];
        const mappingStatus = mapping?.status || 'pending';
        return (
          <article key={claim.id} className="claim-item">
            <div className="claim-head">
              <span className={`status-dot ${mappingStatus}`} />
              <div>
                <h3>{claim.text}</h3>
                <p>
                  {copy.claimType[claim.claim_type] || claim.claim_type} · {copy.confidence} {percent(claim.confidence)}
                </p>
              </div>
            </div>
            <div className="mapping-block">
              <span className={`mapping-status ${mappingStatus}`}>{copy.mapping[mappingStatus] || mappingStatus}</span>
              <p>{mapping?.reasoning || copy.mappingPending}</p>
              {mapping?.evidence_text && <blockquote>{mapping.evidence_text}</blockquote>}
            </div>
          </article>
        );
      })}
    </div>
  );
}

function TraceView({ task, copy }) {
  if (!task?.actions?.length) return <EmptyPanel icon={Bot} text={copy.noTrace} />;
  return (
    <div className="trace-list">
      {task.actions.map((action) => (
        <article key={action.id} className="trace-item">
          <div className="trace-index">{action.step_order}</div>
          <div>
            <div className="trace-title">
              <h3>{action.tool_name}</h3>
              <Badge status={action.status} copy={copy} />
              {action.requires_human_review && <span className="review-chip">{copy.review}</span>}
            </div>
            <p>{action.output_summary}</p>
            <small>{action.input_summary}</small>
          </div>
        </article>
      ))}
    </div>
  );
}

function EvidenceView({ items, copy }) {
  if (!items?.length) return <EmptyPanel icon={ShieldCheck} text={copy.noEvidence} />;
  return (
    <div className="evidence-grid">
      {items.map((item) => (
        <article key={item.id} className="evidence-item">
          <div className="evidence-head">
            <span>{copy.sourceType[item.source_type] || item.source_type}</span>
            <strong>{percent(item.confidence)}</strong>
          </div>
          <blockquote>{item.quote}</blockquote>
          <p>{item.interpretation}</p>
          {item.source_url && (
            <a href={item.source_url} target="_blank" rel="noreferrer">
              <Link2 size={14} />
              <span>{copy.source}</span>
            </a>
          )}
        </article>
      ))}
    </div>
  );
}

function ExperimentsView({ experiments, recommendations, copy }) {
  if (!experiments?.length && !recommendations?.length) {
    return <EmptyPanel icon={FlaskConical} text={copy.noExperiments} />;
  }
  return (
    <div className="experiments-layout">
      <div className="experiment-column">
        <div className="section-label">{copy.experimentBoard}</div>
        {experiments.map((experiment) => (
          <article key={experiment.id} className="experiment-card">
            <div className="experiment-head">
              <h3>{experiment.title}</h3>
              <span className={`priority ${experiment.priority}`}>{copy.priority[experiment.priority] || experiment.priority}</span>
            </div>
            <p>{experiment.hypothesis}</p>
            <strong>{experiment.change_summary}</strong>
            <small>
              {experiment.success_metric} · {copy.effort} {copy.effortValue[experiment.effort] || experiment.effort} · {percent(experiment.confidence)}
            </small>
          </article>
        ))}
      </div>
      <div className="recommendation-column">
        <div className="section-label">{copy.recommendations}</div>
        {recommendations.map((item) => (
          <article key={item.id} className="recommendation-row">
            <BadgeCheck size={17} />
            <div>
              <h3>{item.title}</h3>
              <p>{item.description}</p>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function MetricsView({ rows, summary }) {
  return (
    <div className="metrics-layout">
      <div className="metric-summary">
        <MetricBox label="CTR" value={summary?.ctr_percent || '0.00%'} />
        <MetricBox label="CVR" value={summary?.cvr_percent || '0.00%'} />
        <MetricBox label="CPA" value={summary?.cpa ?? 'n/a'} />
        <MetricBox label="ROAS" value={summary?.roas ?? 0} />
      </div>
      <div className="chart-panel">
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={rows} margin={{ top: 20, right: 20, left: 0, bottom: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#d8dee6" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Line type="monotone" dataKey="cvr" stroke="#2563eb" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="ctr" stroke="#0f766e" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function MetricBox({ label, value }) {
  return (
    <div className="metric-box">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function EmptyPanel({ icon: Icon, text }) {
  return (
    <div className="inline-empty">
      <Icon size={24} />
      <p>{text}</p>
    </div>
  );
}

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.json();
}

function parseMetricsCsv(csv) {
  const lines = csv
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (lines.length <= 1) return [];
  return lines.slice(1).map((line) => {
    const [date, impressions, clicks, conversions, spend, revenue] = line.split(',').map((value) => value.trim());
    return {
      date,
      impressions: Number(impressions || 0),
      clicks: Number(clicks || 0),
      conversions: Number(conversions || 0),
      spend: Number(spend || 0),
      revenue: Number(revenue || 0),
    };
  });
}

function buildMetricRows(metrics) {
  return metrics.map((row) => ({
    date: row.date,
    ctr: row.impressions ? Number(((row.clicks / row.impressions) * 100).toFixed(2)) : 0,
    cvr: row.clicks ? Number(((row.conversions / row.clicks) * 100).toFixed(2)) : 0,
  }));
}

function percent(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function labelize(key) {
  return key
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

export default App;
