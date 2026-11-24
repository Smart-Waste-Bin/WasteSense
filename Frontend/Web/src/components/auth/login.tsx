import { useState, type FormEvent } from "react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import NotchedHeroCard from "./NotchedHeroCard";
import Hero from "@/assets/loginPic.jpeg";
import Logo from "@/assets/logo.jpg";
import { login, type AuthUser } from "@/auth";
import { ForgotPassword } from "./forgot-password";

function Login({ onLogin }: { onLogin: (user: AuthUser) => void }) {
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      const user = await login(email, password, rememberMe);
      onLogin(user);
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : "Sign-in failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (showForgotPassword) {
    return <ForgotPassword onBackToLogin={() => setShowForgotPassword(false)} />;
  }

  return (
    <div className="min-h-screen -my-8 flex justify-center items-center bg-[#f5f5f5] p-6">
      <main className="flex w-[70%] rounded-lg shadow-lg ">
        <section className="relative hidden  overflow-hidden rounded-l-lg bg-white p-12 text-white lg:flex lg:w-[48%] lg:flex-col lg:justify-between">
          <NotchedHeroCard
            src={Hero}
            alt="City skyline seen through an open door"
          />
        </section>
        <section className="flex flex-1 items-center justify-center bg-white px-6 py-12 rounded-r-lg">
          <div className="w-full max-w-[410px]">
            <div className="flex items-center gap-2 mb-6 ">
              <img src={Logo} className="ml-35  h-10 w-10  rounded-sm" />
              <p className="font-logo tracking-tight text-2xl font-bold text-slate-950">
                Smart<span className="text-emerald-700">Bin</span>
              </p>
            </div>

            <h2 className="text-3xl font-bold tracking-tight text-slate-950">
              Welcome Back
            </h2>
            <p className="text-sm leading-6 text-slate-500">
              Access your live waste management overview.
            </p>
            <form className="mt-9 space-y-5" onSubmit={handleSubmit}>
              <label className="block text-sm font-semibold text-slate-700">
                Email or phone
                <Input
                  required
                  type="text"
                  placeholder="you@company.com or 0241234567"
                  className="mt-2"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  autoComplete="username"
                />
              </label>
              <label className="block text-sm font-semibold text-slate-700">
                Password
                <Input
                  required
                  type="password"
                  placeholder="Enter your password"
                  className="mt-2"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete="current-password"
                />
              </label>
              <div className="flex items-center justify-between text-sm">
                <label className="flex items-center gap-2 text-slate-500">
                  <input
                    type="checkbox"
                    className="size-4 accent-emerald-500"
                    checked={rememberMe}
                    onChange={(event) => setRememberMe(event.target.checked)}
                  />{" "}
                  Remember me
                </label>
                <button
                  type="button"
                  onClick={() => setShowForgotPassword(true)}
                  className="font-semibold text-emerald-600 hover:text-emerald-700"
                >
                  Forgot password?
                </button>
              </div>
              <Button
                type="submit"
                disabled={isSubmitting}
                className="h-12 w-full rounded-xl bg-emerald-500 font-bold text-white shadow-lg shadow-emerald-500/20 hover:bg-emerald-600"
              >
                {isSubmitting ? "Signing in..." : "Sign in to dashboard"}
              </Button>
              {error && (
                <p role="alert" className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
                  {error}
                </p>
              )}
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
    </div>
  );
}

export { Login };
