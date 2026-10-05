import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import FloatingOrbs from "@/components/FloatingOrbs";
import Avatar from "@/components/Avatar";
import { Camera, Loader2, ShieldCheck, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";

const MAX_AVATAR_BYTES = 5 * 1024 * 1024;

const Profile = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: me, refetch } = useQuery({ queryKey: ["me"], queryFn: () => api.getMe() });

  const [name, setName] = useState("");
  const [bio, setBio] = useState("");
  const [uploadingAvatar, setUploadingAvatar] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [banner, setBanner] = useState("");

  useEffect(() => {
    if (me) {
      setName(me.name);
      setBio(me.bio ?? "");
    }
  }, [me]);

  const pickAvatar = () => fileInputRef.current?.click();

  const onAvatarSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setError("");
    setBanner("");
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setError("Please choose a JPEG, PNG, or WebP image.");
      return;
    }
    if (file.size > MAX_AVATAR_BYTES) {
      setError("Image must be under 5MB.");
      return;
    }
    setUploadingAvatar(true);
    try {
      await api.uploadAvatar(file);
      await refetch();
      void queryClient.invalidateQueries({ queryKey: ["me"] });
      setBanner("Profile photo updated");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not upload photo");
    } finally {
      setUploadingAvatar(false);
    }
  };

  const saveProfile = async () => {
    setError("");
    setBanner("");
    setSaving(true);
    try {
      await api.updateProfile({ name, bio });
      await refetch();
      void queryClient.invalidateQueries({ queryKey: ["me"] });
      setBanner("Profile saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save profile");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen relative overflow-hidden gradient-bg px-4 py-12">
      <FloatingOrbs />
      <div className="container mx-auto max-w-xl relative z-10">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-10">
          <h1 className="text-4xl font-display font-bold text-foreground mb-3">Your Profile</h1>
          <p className="text-muted-foreground">How you show up to others in the community.</p>
        </motion.div>

        <div className="glass-card-strong p-8 space-y-6">
          <div className="flex flex-col items-center gap-3">
            <button type="button" onClick={pickAvatar} className="relative group" disabled={uploadingAvatar}>
              <Avatar name={me?.name ?? ""} avatarUrl={me?.avatar_url} size="lg" />
              <div className="absolute inset-0 rounded-xl bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                {uploadingAvatar ? (
                  <Loader2 className="w-6 h-6 text-white animate-spin" />
                ) : (
                  <Camera className="w-6 h-6 text-white" />
                )}
              </div>
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={(e) => void onAvatarSelected(e)}
            />
            <button type="button" onClick={pickAvatar} className="text-sm text-primary font-semibold hover:underline">
              Change photo
            </button>
          </div>

          <div className="flex items-center justify-center gap-2">
            {me?.email_verified ? (
              <span className="inline-flex items-center gap-1.5 text-sm text-primary font-medium">
                <ShieldCheck className="w-4 h-4" /> Email verified
              </span>
            ) : (
              <button
                type="button"
                onClick={() => navigate("/verify-email")}
                className="inline-flex items-center gap-1.5 text-sm text-destructive font-medium hover:underline"
              >
                <ShieldAlert className="w-4 h-4" /> Email not verified - finish setup
              </button>
            )}
          </div>

          {banner ? <p className="text-sm text-primary font-medium text-center">{banner}</p> : null}
          {error ? <p className="text-sm text-destructive text-center">{error}</p> : null}

          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} className="mindease-input w-full" />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">
              Bio <span className="text-muted-foreground font-normal">({bio.length}/160)</span>
            </label>
            <textarea
              value={bio}
              onChange={(e) => setBio(e.target.value.slice(0, 160))}
              rows={3}
              placeholder="A line about what you're working through or what helps you - this is what people see before connecting with you."
              className="mindease-input w-full resize-none"
            />
          </div>

          <button
            type="button"
            onClick={() => void saveProfile()}
            disabled={saving}
            className="btn-primary w-full disabled:opacity-60"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin inline mr-2" /> : null}
            Save changes
          </button>
        </div>
      </div>
    </div>
  );
};

export default Profile;
