import { useRef, useState, type ChangeEvent, type FormEvent } from "react";
import {
  changeCurrentUserPassword,
  getPhotoUrl,
  removeCurrentUserPhoto,
  updateCurrentUser,
  uploadCurrentUserPhoto,
  type AuthUser,
} from "@/auth";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Camera, Trash2 } from "lucide-react";
import { toast } from "sonner";

type SettingsProps = {
  onProfileUpdate: (user: AuthUser) => void;
  user: AuthUser;
};

function Settings({ onProfileUpdate, user }: SettingsProps) {
  const [name, setName] = useState(user.name);
  const [phone, setPhone] = useState(user.phone ?? "");
  const [isSaving, setIsSaving] = useState(false);
  const [isPhotoUpdating, setIsPhotoUpdating] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const photoInputRef = useRef<HTMLInputElement>(null);
  const photoUrl = getPhotoUrl(user.photo_url);
  const isBusy = isSaving || isPhotoUpdating || isChangingPassword;

  const handlePhotoChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const photo = event.target.files?.[0];
    event.target.value = "";
    if (!photo) return;

    setIsPhotoUpdating(true);
    try {
      const updatedUser = await uploadCurrentUserPhoto(photo);
      onProfileUpdate(updatedUser);
      toast.success("Profile photo updated");
    } catch (photoError) {
      const message =
        photoError instanceof Error
          ? photoError.message
          : "Profile photo upload failed.";
      toast.error("Could not update profile photo", { description: message });
    } finally {
      setIsPhotoUpdating(false);
    }
  };

  const handleRemovePhoto = async () => {
    setIsPhotoUpdating(true);
    try {
      const updatedUser = await removeCurrentUserPhoto();
      onProfileUpdate(updatedUser);
      toast.success("Profile photo removed");
    } catch (photoError) {
      const message =
        photoError instanceof Error
          ? photoError.message
          : "Profile photo removal failed.";
      toast.error("Could not remove profile photo", { description: message });
    } finally {
      setIsPhotoUpdating(false);
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSaving(true);
    try {
      const updatedUser = await updateCurrentUser({
        name: name.trim(),
        phone: phone.trim() || null,
      });
      onProfileUpdate(updatedUser);
      setName(updatedUser.name);
      setPhone(updatedUser.phone ?? "");
      toast.success("Profile updated", {
        description: "Your account details have been saved.",
      });
    } catch (saveError) {
      const message =
        saveError instanceof Error
          ? saveError.message
          : "Profile update failed.";
      toast.error("Could not update profile", { description: message });
    } finally {
      setIsSaving(false);
    }
  };

  const handlePasswordSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsChangingPassword(true);
    try {
      const updatedUser = await changeCurrentUserPassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      onProfileUpdate({ ...updatedUser, photo_url: user.photo_url });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      toast.success("Password updated", {
        description: "Your other signed-in devices have been logged out.",
      });
    } catch (changeError) {
      const message =
        changeError instanceof Error
          ? changeError.message
          : "Password change failed.";
      toast.error("Could not update password", { description: message });
    } finally {
      setIsChangingPassword(false);
    }
  };

  return (
    <main className="mx-auto w-full max-w-[1440px] min-w-0 px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">
          Settings
        </h1>
        <p className="mt-2 text-sm text-slate-500">
          Manage your account details and preferences.
        </p>
      </div>
      <div className="flex items-center justify-center">
        <section className="w-4/5 max-w-3xl rounded-2xl border border-slate-200 bg-white shadow-sm items-center justify-center">
          <div className="border-b border-slate-100 px-6 py-5 sm:px-8">
            <h2 className="text-lg font-bold text-slate-950">Profile</h2>
            <p className="mt-1 text-sm text-slate-500">
              Update the personal details associated with your account.
            </p>
          </div>
          <form onSubmit={handleSubmit} className="space-y-5 px-6 py-6 sm:px-8">
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex size-20 shrink-0 items-center justify-center overflow-hidden rounded-full bg-emerald-100 text-xl font-bold text-emerald-700">
                {photoUrl ? (
                  <img
                    src={photoUrl}
                    alt={`${user.name}'s profile`}
                    className="size-full object-cover"
                  />
                ) : (
                  user.name
                    .split(" ")
                    .map((part) => part[0])
                    .join("")
                    .slice(0, 2)
                    .toUpperCase()
                )}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <input
                  ref={photoInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handlePhotoChange}
                  className="sr-only"
                  aria-label="Choose a profile picture"
                />
                <Button
                  type="button"
                  variant="outline"
                  disabled={isBusy}
                  onClick={() => photoInputRef.current?.click()}
                >
                  <Camera size={16} />
                  {isPhotoUpdating ? "Updating photo..." : "Change photo"}
                </Button>
                {user.photo_url && (
                  <Button
                    type="button"
                    variant="ghost"
                    disabled={isBusy}
                    onClick={handleRemovePhoto}
                    className="text-slate-500 hover:text-red-600"
                  >
                    <Trash2 size={16} />
                    Remove
                  </Button>
                )}
                <span className="w-full text-xs text-slate-400">
                  JPEG, PNG or WebP. Maximum file size: 2 MB.
                </span>
              </div>
            </div>
            <label className="block text-sm font-semibold text-slate-700">
              Full name
              <Input
                required
                maxLength={100}
                autoComplete="name"
                value={name}
                onChange={(event) => {
                  setName(event.target.value);
                }}
                className="mt-2 h-11 rounded-xl"
              />
            </label>
            <label className="block text-sm font-semibold text-slate-700">
              Email address
              <Input
                type="email"
                value={user.email}
                readOnly
                aria-describedby="settings-email-help"
                className="mt-2 h-11 rounded-xl bg-slate-50 text-slate-500"
              />
              <span
                id="settings-email-help"
                className="mt-1 block text-xs font-normal text-slate-400"
              >
                Contact an administrator to change your email.
              </span>
            </label>
            <label className="block text-sm font-semibold text-slate-700">
              Phone number
              <Input
                type="tel"
                autoComplete="tel"
                value={phone}
                onChange={(event) => {
                  setPhone(event.target.value);
                }}
                placeholder="024 123 4567"
                className="mt-2 h-11 rounded-xl"
              />
            </label>
            <div className="flex justify-end border-t border-slate-100 pt-5">
              <Button
                type="submit"
                disabled={isBusy}
                className="rounded-lg bg-emerald-600 text-white hover:bg-emerald-700"
              >
                {isSaving ? "Saving..." : "Save changes"}
              </Button>
            </div>
          </form>
        </section>
      </div>

      <div className="flex items-center justify-center">
        <section className="mt-6 w-4/5 max-w-3xl rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-100 px-6 py-5 sm:px-8">
            <h2 className="text-lg font-bold text-slate-950">
              Change password
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Choose a new password with at least 8 characters.
            </p>
          </div>
          <form
            onSubmit={handlePasswordSubmit}
            className="space-y-5 px-6 py-6 sm:px-8"
          >
            <label className="block text-sm font-semibold text-slate-700">
              Current password
              <Input
                required
                type="password"
                maxLength={128}
                autoComplete="current-password"
                value={currentPassword}
                onChange={(event) => {
                  setCurrentPassword(event.target.value);
                }}
                className="mt-2 h-11 rounded-xl"
              />
            </label>
            <label className="block text-sm font-semibold text-slate-700">
              New password
              <Input
                required
                type="password"
                minLength={8}
                maxLength={128}
                autoComplete="new-password"
                value={newPassword}
                onChange={(event) => {
                  setNewPassword(event.target.value);
                }}
                className="mt-2 h-11 rounded-xl"
              />
            </label>
            <label className="block text-sm font-semibold text-slate-700">
              Confirm new password
              <Input
                required
                type="password"
                minLength={8}
                maxLength={128}
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(event) => {
                  setConfirmPassword(event.target.value);
                }}
                className="mt-2 h-11 rounded-xl"
              />
            </label>
            <div className="flex justify-end border-t border-slate-100 pt-5">
              <Button
                type="submit"
                disabled={isBusy}
                className="rounded-lg bg-emerald-600 text-white hover:bg-emerald-700"
              >
                {isChangingPassword
                  ? "Updating password..."
                  : "Update password"}
              </Button>
            </div>
          </form>
        </section>
      </div>
    </main>
  );
}

export { Settings };
