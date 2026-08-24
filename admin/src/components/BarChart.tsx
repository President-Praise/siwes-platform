interface Point { label: string; value: number; }

export function BarChart({ data, height = 160, formatValue }: { data: Point[]; height?: number; formatValue?: (v: number) => string }) {
  if (data.length === 0) return <div className="text-gray-500 text-sm py-4">No data yet.</div>;
  const max = Math.max(...data.map(d => d.value), 1);
  return (
    <div>
      <div className="flex items-end gap-1 border-b border-gray-200" style={{ height }}>
        {data.map((d, i) => {
          const h = Math.round((d.value / max) * (height - 20));
          return (
            <div key={i} className="flex-1 flex flex-col items-center group">
              <div
                className="w-full bg-navy hover:bg-gold transition rounded-t"
                style={{ height: `${h}px` }}
                title={`${d.label}: ${formatValue ? formatValue(d.value) : d.value}`}
              />
            </div>
          );
        })}
      </div>
      <div className="flex gap-1 mt-1">
        {data.map((d, i) => (
          <div key={i} className="flex-1 text-[10px] text-gray-500 text-center overflow-hidden">{d.label.slice(-5)}</div>
        ))}
      </div>
    </div>
  );
}
