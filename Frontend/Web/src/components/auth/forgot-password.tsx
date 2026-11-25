import { ArrowLeft } from "lucide-react";
import { Button } from "../ui/button";
import Logo from "@/assets/logo.jpg";

function ForgotPassword({ onBackToLogin }: { onBackToLogin: () => void }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#f5f5f5] p-6">
      <main className="w-full max-w-lg rounded-3xl bg-white p-7 shadow-lg sm:p-10">
        <button
          type="button"
          onClick={onBackToLogin}
          className="mb-8 inline-flex items-center gap-2 text-sm font-semibold text-slate-500 transition-colors hover:text-emerald-700"
        >
          <ArrowLeft size={16} />
          Back to sign in
        </button>

        <div className="mb-7 flex items-center justify-center gap-2">
          <img
            src={Logo}
            alt="SmartBin logo"
            className="h-10 w-10 rounded-sm"
          />
          <p className="font-logo text-2xl font-bold tracking-tight text-slate-950">
            Smart<span className="text-emerald-700">Bin</span>
          </p>
        </div>

        <h1 className="text-3xl font-bold tracking-tight text-slate-950">
          Forgot your password?
        </h1>
        <p className="mt-3 text-sm leading-6 text-slate-500">
          Password resets are managed by your organization. Contact your
          administrator to verify your account and reset your password.
        </p>

        <div className="mt-8 rounded-xl border border-emerald-100 bg-emerald-50/70 px-4 py-3 text-sm leading-6 text-emerald-900">
          For your security, don’t share your password with anyone.
        </div>

        <Button
          type="button"
          onClick={onBackToLogin}
          className="mt-8 h-12 w-full rounded-xl bg-emerald-600 font-bold text-white hover:bg-emerald-700"
        >
          Return to sign in
        </Button>
      </main>
    </div>
  );
}

export { ForgotPassword };
