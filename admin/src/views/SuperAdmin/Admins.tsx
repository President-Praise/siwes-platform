import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type School } from "../../api";
import { Spinner } from "../../components/Spinner";

export function SuperAdmins() {
  const [schools, setSchools] = useState<School[] | null>(null);
  useEffect(() => { api.superListSchools().then(setSchools); }, []);
  if (!schools) return <Spinner />;
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-head text-navy">School admins</h1>
      <p className="text-sm text-gray-500">Manage admin users per school. Click a school to add or reset admins.</p>
      <div className="card space-y-2">
        {schools.map(s => (
          <Link key={s.id} to={`/schools/${s.id}`} className="block p-3 rounded hover:bg-gray-50 border border-gray-100">
            <div className="font-semibold text-navy">{s.name}</div>
            <div className="text-xs text-gray-500">/{s.slug} · {s.full_name}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
