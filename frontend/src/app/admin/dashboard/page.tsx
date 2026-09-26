"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, clearTokens, UserOut } from "@/lib/api";

interface AnalyticsSummary {
  total_students: number;
  total_instructors: number;
  total_courses: number;
  average_gpa: number | null;
  average_attendance_percentage: number | null;
  production_models: { name: string; version: string; task_type: string }[];
}

export default function AdminDashboard() {
  const router = useRouter();
  const [user, setUser] = useState<UserOut | null>(null);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .me()
      .then((u) => {
        setUser(u);
        return fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/analytics/university`, {
          headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` },
        });
      })
      .then(async (res) => {
        if (!res.ok) throw new ApiError(res.status, "error", "Could not load analytics.");
        setSummary(await res.json());
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) router.push("/login");
        else setError("Could not load university analytics.");
      });
  }, [router]);

  function logout() {
    clearTokens();
    router.push("/login");
  }

  const cards = summary
    ? [
        { label: "Total Students", value: summary.total_students },
        { label: "Total Instructors", value: summary.total_instructors },
        { label: "Total Courses", value: summary.total_courses },
        { label: "Average GPA", value: summary.average_gpa ?? "—" },
        {
          label: "Average Attendance",
          value: summary.average_attendance_percentage ? `${summary.average_attendance_percentage}%` : "—",
        },
      ]
    : [];

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold text-slate-900">Admin Dashboard</h1>
          {user && <p className="text-sm text-slate-500">Signed in as {user.name}</p>}
        </div>
        <button onClick={logout} className="text-sm text-slate-500 hover:text-slate-900">
          Sign out
        </button>
      </header>

      <main className="mx-auto max-w-5xl space-y-6 px-6 py-8">
        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {cards.map((c) => (
            <div key={c.label} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-xs text-slate-500">{c.label}</p>
              <p className="mt-1 text-2xl font-bold text-slate-900">{c.value}</p>
            </div>
          ))}
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-base font-semibold text-slate-900">Production ML Models</h2>
          <p className="text-sm text-slate-500">The model currently serving live predictions for each task.</p>
          <table className="mt-4 w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-slate-500">
                <th className="pb-2">Task</th>
                <th className="pb-2">Model</th>
                <th className="pb-2">Version</th>
              </tr>
            </thead>
            <tbody>
              {summary?.production_models.length ? (
                summary.production_models.map((m, i) => (
                  <tr key={i} className="border-b border-slate-100">
                    <td className="py-2">{m.task_type}</td>
                    <td className="py-2">{m.name}</td>
                    <td className="py-2">{m.version}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={3} className="py-3 text-slate-400">
                    No production model registered in the database yet — models are currently promoted via the file
                    registry (ml/inference/registry/production.json). Registering ml_models rows is a documented
                    follow-up (see docs/machine-learning.md).
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
