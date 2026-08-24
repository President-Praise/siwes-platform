import { useEffect, useState } from "react";
import { api, fmtDate, fmtNaira, type Order } from "../../api";
import { StatusBadge } from "../../components/StatusBadge";

export function OrderDrawer({ order, onClose, onChange }: { order: Order; onClose: () => void; onChange: () => void }) {
  const [detail, setDetail] = useState<any>(null);
  const [notes, setNotes] = useState(order.notes || "");
  useEffect(() => { api.schoolOrderDetail(order.id).then(d => { setDetail(d); setNotes(d.order.notes || ""); }); }, [order.id]);

  async function action(fn: () => Promise<any>) {
    try { await fn(); onChange(); api.schoolOrderDetail(order.id).then(setDetail); } catch (e: any) { alert(e.message); }
  }

  return (
    <div className="fixed inset-0 z-40 flex">
      <div className="flex-1 bg-black/30" onClick={onClose} />
      <div className="w-full max-w-2xl bg-white shadow-lg overflow-y-auto">
        <div className="p-5 border-b border-gray-200 flex justify-between items-start">
          <div>
            <div className="text-xs text-gray-500">Order #{order.id}</div>
            <h2 className="text-xl font-head text-navy">{order.student_name}</h2>
            <div className="text-sm text-gray-600">{order.matric_no} · {order.student_email}</div>
          </div>
          <button onClick={onClose} className="text-gray-500 text-2xl leading-none">×</button>
        </div>
        <div className="p-5 space-y-4">
          <div className="flex gap-3 items-center text-sm">
            <StatusBadge status={order.status} />
            <span>{order.package}</span>
            <span className="text-gray-500">·</span>
            <span>{fmtNaira(order.amount)}</span>
            <span className="text-gray-500">·</span>
            <span>{fmtDate(order.created_at, true)}</span>
          </div>

          <div className="grid grid-cols-3 gap-2 text-sm">
            <Stat label="Platform fee" value={fmtNaira(order.platform_amount)} />
            <Stat label="Your share" value={fmtNaira(order.admin_amount)} />
            <Stat label="Referral" value={order.referral_code || "—"} />
          </div>

          <div className="flex gap-2 flex-wrap">
            {order.status === "failed" && <button className="btn btn-secondary" onClick={() => action(() => api.schoolRetry(order.id))}>Retry</button>}
            {order.status === "generated" && !order.delivered_at && <button className="btn btn-secondary" onClick={() => action(() => api.schoolDeliver(order.id))}>Mark delivered</button>}
            {order.status === "generated" && !order.printed_at && <button className="btn btn-secondary" onClick={() => action(() => api.schoolMarkPrinted(order.id))}>Mark printed</button>}
            {order.docx_path && <a className="btn btn-gold" href={`/admin/api/school/orders/${order.id}/notes`} onClick={e => { e.preventDefault(); window.open(`/`); }} style={{ display: 'none' }}>DOCX</a>}
          </div>

          {order.docx_path && (
            <div className="text-sm">
              <a className="text-navy underline" href={`/${detail?.school_slug || ''}`} onClick={e => { e.preventDefault(); }}>Generated files exist on server.</a>
            </div>
          )}

          <div>
            <label className="label">Notes</label>
            <textarea className="input" rows={3} value={notes} onChange={e => setNotes(e.target.value)} />
            <button className="btn btn-secondary mt-2 text-sm" onClick={() => action(() => api.schoolUpdateNotes(order.id, notes))}>Save notes</button>
          </div>

          {order.error_message && (
            <div className="bg-red-50 border-l-4 border-red-400 p-3 text-sm">
              <div className="font-semibold text-red-800">Error</div>
              <pre className="whitespace-pre-wrap mt-1 text-xs">{order.error_message}</pre>
            </div>
          )}

          {detail?.logs && (
            <div>
              <h3 className="font-semibold text-navy mb-2">Generation log</h3>
              <ul className="text-xs space-y-1 font-mono max-h-64 overflow-y-auto bg-gray-50 p-3 rounded">
                {detail.logs.map((l: any) => (
                  <li key={l.id}><span className="text-gray-500">{l.timestamp.slice(11, 19)}</span> [{l.level}] {l.message}{l.duration_ms ? ` (${l.duration_ms}ms)` : ""}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return <div className="bg-gray-50 rounded p-2"><div className="text-[10px] uppercase text-gray-500">{label}</div><div className="font-semibold">{value}</div></div>;
}
