"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, clearTokens, PredictionResponse, UserOut } from "@/lib/api";
import { RiskBadge } from "@/components/RiskBadge";

interface RosterEntry {
  student_profile_id: number;
  student_id: string;
  enrollment_id: number;
}

export default function InstructorDashboard() {
  const router = useRouter();
  const [user, setUser] = useState<UserOut | null>(null);
  const [courseIdInput, setCourseIdInput] = useState("");
  const [roster, setRoster] = useState<RosterEntry[] | null>(null);
  const [predictions, setPredictions] = useState<Record<number, PredictionResponse>>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch(() => router.push("/login"));
  }, [router]);

  async function loadRoster() {
    setError(null);
    setLoading(true);
    setRoster(null);
    setPredictions({});
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/courses/${courseIdInput}/students`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` },
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new ApiError(res.status, body.code ?? "error", body.message ?? "Could not load roster.");
      }
      setRoster(await res.json());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load roster.");
    } finally {
      setLoading(false);
    }
  }

  async function loadPrediction(studentProfileId: number) {
    try {
      const result = await api.generatePrediction(studentProfileId);
      setPredictions((prev) => ({ ...prev, [studentProfileId]: result }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not generate prediction for this student.");
    }
  }

  function logout() {
    clearTokens();
    router.push("/login");
  }

  const atRiskCount = Object.values(predictions).filter((p) => p.classification.risk_level === "HIGH").length;

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold text-slate-900">Instructor Dashboard</h1>
          {user && <p className="text-sm text-slate-500">Signed in as {user.name}</p>}
        </div>
        <button onClick={logout} className="text-sm text-slate-500 hover:text-slate-900">
          Sign out
        </button>
      </header>

      <main className="mx-auto max-w-4xl space-y-6 px-6 py-8">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-base font-semibold text-slate-900">Load your course roster</h2>
          <p className="mt-1 text-sm text-slate-500">
            You can only load rosters for courses you are assigned to teach; anything else returns a 403.
          </p>
          <div className="mt-4 flex gap-2">
            <input
              value={courseIdInput}
              onChange={(e) => setCourseIdInput(e.target.value)}
              placeholder="Course ID"
              className="w-40 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-900 focus:outline-none"
            />
            <button
              onClick={loadRoster}
              disabled={loading}
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
            >
              {loading ? "Loading…" : "Load roster"}
            </button>
          </div>
          {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        </div>

        {roster && (
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-base font-semibold text-slate-900">Roster ({roster.length} students)</h3>
              {atRiskCount > 0 && (
                <span className="text-sm font-medium text-red-600">{atRiskCount} at-risk student(s) flagged</span>
              )}
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-slate-500">
                  <th className="pb-2">Student ID</th>
                  <th className="pb-2">Predicted GPA</th>
                  <th className="pb-2">Risk</th>
                  <th className="pb-2"></th>
                </tr>
              </thead>
              <tbody>
                {roster.map((r) => {
                  const p = predictions[r.student_profile_id];
                  return (
                    <tr key={r.enrollment_id} className="border-b border-slate-100">
                      <td className="py-2">{r.student_id}</td>
                      <td className="py-2">{p ? p.regression.predicted_gpa.toFixed(2) : "—"}</td>
                      <td className="py-2">{p ? <RiskBadge level={p.classification.risk_level} /> : "—"}</td>
                      <td className="py-2 text-right">
                        <button
                          onClick={() => loadPrediction(r.student_profile_id)}
                          className="text-xs font-medium text-slate-600 hover:text-slate-900"
                        >
                          {p ? "Refresh" : "Predict"}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
