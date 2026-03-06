import React from 'react'
import { createRoot } from 'react-dom/client'
import { LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts'
import './styles.css'

const apiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

function useData(path, fallback = []) {
  const [data, setData] = React.useState(fallback)
  React.useEffect(() => {
    fetch(`${apiBase}${path}`)
      .then((res) => res.json())
      .then(setData)
      .catch(() => setData(fallback))
  }, [path])
  return data
}

function App() {
  const trend = useData('/costs/trend', [{ date: '2026-03-01', total_daily_cost: 10 }])
  const byService = useData('/costs/by-service', [{ service: 'compute_instance', total_daily_cost: 6 }])
  const byCompartment = useData('/costs/by-compartment', [{ compartment: 'prod', total_daily_cost: 8 }])
  const resources = useData('/resources', [])

  const daily = trend.at(-1)?.total_daily_cost ?? 0
  const monthly = trend.reduce((a, b) => a + b.total_daily_cost, 0)
  const colors = ['#2F80ED', '#27AE60', '#F2994A', '#9B51E0', '#56CCF2']

  return (
    <main className="container">
      <h1>CloudCostLens - OCI Cost Visibility</h1>
      <section className="kpis">
        <article><h3>Daily Cost</h3><p>${daily.toFixed(2)}</p></article>
        <article><h3>Monthly Cost</h3><p>${monthly.toFixed(2)}</p></article>
        <article><h3>Resources</h3><p>{resources.length}</p></article>
      </section>

      <section className="grid">
        <div className="card">
          <h3>Cost Trend</h3>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={trend}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="total_daily_cost" stroke="#2F80ED" />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="card">
          <h3>Cost by Service</h3>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={byService} dataKey="total_daily_cost" nameKey="service" outerRadius={90} label>
                {byService.map((_, idx) => <Cell key={idx} fill={colors[idx % colors.length]} />)}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="card">
        <h3>Cost by Compartment</h3>
        <table>
          <thead><tr><th>Compartment</th><th>Daily Cost</th></tr></thead>
          <tbody>
            {byCompartment.map((c) => (
              <tr key={c.compartment}><td>{c.compartment}</td><td>${c.total_daily_cost.toFixed(2)}</td></tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  )
}

createRoot(document.getElementById('root')).render(<App />)
