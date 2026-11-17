import type { FormEvent } from "react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";


function Login({ onLogin }: { onLogin: () => void }) {
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onLogin();
  };

  return (
    <main className="flex min-h-screen bg-slate-950">
      <section className="relative hidden overflow-hidden bg-emerald-600 p-12 text-white lg:flex lg:w-[48%] lg:flex-col lg:justify-between">
        <div className="absolute -right-36 -top-32 size-[520px] rounded-full border-[80px] border-white/10" />
        <div className="absolute -bottom-48 -left-20 size-[440px] rounded-full border-[70px] border-white/10" />
        
        <div className="relative max-w-md">
          <p className="mb-5 text-sm font-bold uppercase tracking-[0.2em] text-emerald-100">
            Cleaner cities. Smarter future.
          </p>
          <h1 className="text-5xl font-bold leading-[1.08] tracking-tight">
            Make every collection count.
          </h1>
          <p className="mt-6 text-lg leading-8 text-emerald-50">
            Monitor your waste network, reduce unnecessary pickups, and build a
            more sustainable city with real-time intelligence.
          </p>
        </div>
        <p className="relative text-sm text-emerald-100">
          © 2025 WasteSense. Built for a cleaner tomorrow.
        </p>
      </section>
      <section className="flex flex-1 items-center justify-center bg-slate-50 px-6 py-12">
        <div className="w-full max-w-[410px]">
          <div className="mb-10 lg:hidden">
           
          </div>
          <p className="mb-3 text-sm font-semibold text-emerald-600">
            Welcome back
          </p>
          <h2 className="text-3xl font-bold tracking-tight text-slate-950">
            Sign in to WasteSense
          </h2>
          <p className="mt-3 text-sm leading-6 text-slate-500">
            Access your live waste management overview.
          </p>
          <form className="mt-9 space-y-5" onSubmit={handleSubmit}>
            <label className="block text-sm font-semibold text-slate-700">
              Work email
              <Input
                required
                type="email"
                placeholder="you@company.com"
                className="mt-2"
              />
            </label>
            <label className="block text-sm font-semibold text-slate-700">
              Password
              <Input
                required
                type="password"
                placeholder="Enter your password"
                className="mt-2"
              />
            </label>
            <div className="flex items-center justify-between text-sm">
              <label className="flex items-center gap-2 text-slate-500">
                <input type="checkbox" className="size-4 accent-emerald-500" />{" "}
                Remember me
              </label>
              <button
                type="button"
                className="font-semibold text-emerald-600 hover:text-emerald-700"
              >
                Forgot password?
              </button>
            </div>
            <Button
              type="submit"
              className="h-12 w-full rounded-xl bg-emerald-500 font-bold text-white shadow-lg shadow-emerald-500/20 hover:bg-emerald-600"
            >
              Sign in to dashboard
            </Button>
          </form>
          <p className="mt-8 text-center text-sm text-slate-500">
            Need access?{" "}
            <button className="font-semibold text-emerald-600">
              Contact your administrator
            </button>
          </p>
        </div>
      </section>
    </main>
  );
}

export { Login };
