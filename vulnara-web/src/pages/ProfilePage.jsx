import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";

const ROLE_COLORS = {
  admin: "text-red-400 border-red-400/40 bg-red-400/10",
  analyst: "text-blue-400 border-blue-400/40 bg-blue-400/10",
  client: "text-green-400 border-green-400/40 bg-green-400/10",
};

function FieldGroup({ label, children }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-[11px] uppercase tracking-widest font-semibold text-on-surface-variant/70">
        {label}
      </label>
      {children}
    </div>
  );
}

function InputField({ value, onChange, type = "text", placeholder, disabled }) {
  return (
    <input
      type={type}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      disabled={disabled}
      className="w-full bg-[#0d1117] border border-outline-variant rounded-lg px-4 py-2.5 text-sm text-on-surface
                 placeholder:text-on-surface-variant/40 focus:outline-none focus:border-primary/60 transition-colors
                 disabled:opacity-40 disabled:cursor-not-allowed"
    />
  );
}

export function ProfilePage() {
  const { user, login } = useAuth();
  const qc = useQueryClient();

  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const mutation = useMutation({
    mutationFn: (payload) => api.updateProfile(payload),
    onSuccess: (updated) => {
      // Refresh the auth context user data
      qc.invalidateQueries({ queryKey: ["me"] });
      setSuccessMsg("Profile updated successfully!");
      setErrorMsg("");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    },
    onError: (err) => {
      setErrorMsg(err.message);
      setSuccessMsg("");
    },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    setSuccessMsg("");
    setErrorMsg("");

    if (newPassword && newPassword !== confirmPassword) {
      setErrorMsg("New passwords do not match.");
      return;
    }
    if (newPassword && newPassword.length < 8) {
      setErrorMsg("New password must be at least 8 characters.");
      return;
    }

    const payload = {};
    if (fullName !== user?.full_name) payload.full_name = fullName;
    if (email !== user?.email) payload.email = email;
    if (newPassword) {
      payload.current_password = currentPassword;
      payload.new_password = newPassword;
    }

    if (Object.keys(payload).length === 0) {
      setErrorMsg("No changes detected.");
      return;
    }

    mutation.mutate(payload);
  };

  const initials = user?.full_name?.slice(0, 2)?.toUpperCase() || "??";
  const roleClass = ROLE_COLORS[user?.role] || ROLE_COLORS.client;

  return (
    <div className="p-container-padding max-w-2xl mx-auto flex flex-col gap-8">
      {/* Header */}
      <div>
        <h2 className="font-display-lg text-display-lg text-on-surface flex items-center gap-3">
          <span className="material-symbols-outlined text-primary text-[32px]">manage_accounts</span>
          Profile Settings
        </h2>
        <p className="text-on-surface-variant mt-2 font-body-md">
          Update your display name, email address, or change your password.
        </p>
      </div>

      {/* Avatar + Role Card */}
      <div className="glass-panel rounded-xl p-6 flex items-center gap-5">
        <div
          className="w-16 h-16 rounded-full flex items-center justify-center text-xl font-bold text-primary
                     bg-gradient-to-br from-primary/20 to-primary/5 border-2 border-primary/30 shrink-0"
          style={{ boxShadow: "0 0 24px rgba(200,198,197,0.15)" }}
        >
          {initials}
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-on-surface font-semibold text-base">{user?.full_name}</span>
          <span className="text-on-surface-variant text-sm">{user?.email}</span>
          <span className={`text-[10px] uppercase tracking-widest font-bold border rounded-full px-2.5 py-0.5 self-start mt-1 ${roleClass}`}>
            {user?.role}
          </span>
        </div>
      </div>

      {/* Edit Form */}
      <form onSubmit={handleSubmit} className="glass-panel rounded-xl p-6 flex flex-col gap-6">
        <h3 className="font-headline-sm text-on-surface border-b border-outline-variant/30 pb-3">
          Account Information
        </h3>

        <FieldGroup label="Full Name">
          <InputField
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Your full name"
          />
        </FieldGroup>

        <FieldGroup label="Email Address">
          <InputField
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="your@email.com"
          />
        </FieldGroup>

        <h3 className="font-headline-sm text-on-surface border-b border-outline-variant/30 pb-3 pt-2">
          Change Password
          <span className="text-[11px] font-normal text-on-surface-variant ml-2">(leave blank to keep current)</span>
        </h3>

        <FieldGroup label="Current Password">
          <InputField
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            placeholder="Required to change password"
          />
        </FieldGroup>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <FieldGroup label="New Password">
            <InputField
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Min. 8 characters"
            />
          </FieldGroup>
          <FieldGroup label="Confirm New Password">
            <InputField
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Repeat new password"
            />
          </FieldGroup>
        </div>

        {/* Feedback Messages */}
        {successMsg && (
          <div className="flex items-center gap-2 bg-green-500/10 border border-green-500/30 text-green-400 rounded-lg px-4 py-3 text-sm">
            <span className="material-symbols-outlined text-[18px]" style={{ fontVariationSettings: "'FILL' 1" }}>check_circle</span>
            {successMsg}
          </div>
        )}
        {errorMsg && (
          <div className="flex items-center gap-2 bg-error/10 border border-error/30 text-error rounded-lg px-4 py-3 text-sm">
            <span className="material-symbols-outlined text-[18px]" style={{ fontVariationSettings: "'FILL' 1" }}>error</span>
            {errorMsg}
          </div>
        )}

        <button
          type="submit"
          disabled={mutation.isPending}
          className="self-start bg-primary text-on-primary px-6 py-2.5 rounded-lg font-bold text-sm
                     hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                     shadow-[0_0_15px_rgba(200,198,197,0.2)] flex items-center gap-2"
        >
          {mutation.isPending ? (
            <>
              <span className="material-symbols-outlined text-[16px] animate-spin">progress_activity</span>
              Saving…
            </>
          ) : (
            <>
              <span className="material-symbols-outlined text-[16px]">save</span>
              Save Changes
            </>
          )}
        </button>
      </form>
    </div>
  );
}
