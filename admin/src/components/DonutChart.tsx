interface Slice { label: string; value: number; color: string; }

export function DonutChart({ data, size = 140 }: { data: Slice[]; size?: number }) {
  const total = data.reduce((acc, s) => acc + s.value, 0);
  if (total === 0) return <div className="text-gray-500 text-sm py-4">No data yet.</div>;
  const r = size / 2 - 10;
  const cx = size / 2;
  const cy = size / 2;
  let acc = 0;
  return (
    <div className="flex items-center gap-4">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {data.map((s, i) => {
          const start = (acc / total) * Math.PI * 2 - Math.PI / 2;
          acc += s.value;
          const end = (acc / total) * Math.PI * 2 - Math.PI / 2;
          const large = end - start > Math.PI ? 1 : 0;
          const x1 = cx + Math.cos(start) * r;
          const y1 = cy + Math.sin(start) * r;
          const x2 = cx + Math.cos(end) * r;
          const y2 = cy + Math.sin(end) * r;
          return (
            <path
              key={i}
              d={`M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`}
              fill={s.color}
            />
          );
        })}
        <circle cx={cx} cy={cy} r={r * 0.55} fill="#fff" />
        <text x={cx} y={cy + 4} textAnchor="middle" fontSize="14" fontWeight="600" fill="#1E3A5F">{total}</text>
      </svg>
      <ul className="text-xs space-y-1">
        {data.map((s, i) => (
          <li key={i} className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-sm" style={{ background: s.color }} />
            <span>{s.label}: {s.value}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
