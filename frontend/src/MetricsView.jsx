import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';


export default function MetricsView({ rows, summary }) {
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
