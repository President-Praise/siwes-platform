import { useEffect, useState } from "react";
import { api, fmtDate, fmtNaira } from "../../api";
import { Spinner } from "../../components/Spinner";

export function SchoolStudents() {
  const [students, setStudents] = useState<any[] | null>(null);
  useEffect(() => { api.schoolStudents().then(setStudents); }, []);
  if (!students) return <Spinner />;
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-head text-navy">Students</h1>
      <div className="card p-0 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500">
            <tr><th className="text-left p-3">Matric</th><th className="text-left p-3">Name</th><th className="text-left p-3">Email</th><th className="text-right p-3">Orders</th><th className="text-right p-3">Total spent</th><th className="text-left p-3">Last</th></tr>
          </thead>
          <tbody>
            {students.map(s => (
              <tr key={s.matric_no} className="border-t border-gray-100">
                <td className="p-3 font-mono text-xs">{s.matric_no}</td>
                <td className="p-3">{s.student_name}</td>
                <td className="p-3 text-gray-600">{s.email}</td>
                <td className="p-3 text-right">{s.order_count}</td>
                <td className="p-3 text-right">{fmtNaira(s.total_spent)}</td>
                <td className="p-3 text-gray-500">{fmtDate(s.last_at, true)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
