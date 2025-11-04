import React, {useState, useEffect} from "react";
import axios from "axios";
import { useSearchParams } from "react-router-dom";

export default function ResetPassword(){
  const [searchParams] = useSearchParams();
  const [token, setToken] = useState(searchParams.get("token") || "");
  const [password, setPassword] = useState("");
  const [msg, setMsg] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    try {
      const res = await axios.post("http://localhost:8000/reset-password", { token, new_password: password });
      setMsg(res.data.message || "Password reset successful. You may now login.");
    } catch (err) {
      setMsg(err.response?.data?.detail || "Reset failed");
    }
  };

  useEffect(()=> {
    const q = searchParams.get("token");
    if (q) setToken(q);
  }, [searchParams]);

  return (
    <div className="max-w-md mx-auto bg-white p-6 rounded shadow">
      <h2 className="text-xl font-semibold mb-4">Reset password</h2>
      <form onSubmit={submit}>
        <input value={token} onChange={e=>setToken(e.target.value)} placeholder="paste token or use link" className="w-full p-2 border rounded mb-2" />
        <input value={password} onChange={e=>setPassword(e.target.value)} placeholder="new password" type="password" className="w-full p-2 border rounded" />
        <button className="mt-3 w-full bg-accent text-white py-2 rounded">Set new password</button>
      </form>
      <div className="mt-3 text-sm text-gray-700">{msg}</div>
    </div>
  );
}
