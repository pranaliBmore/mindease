import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import FloatingOrbs from "@/components/FloatingOrbs";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Users,
  MessageCircle,
  UserPlus,
  Globe,
  ArrowRight,
  Heart,
  Loader2,
  Search,
  Send,
  Check,
  X,
  Clock,
} from "lucide-react";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { useSocialWebSocket } from "@/hooks/useSocialWebSocket";
import { api, type CommunityPost, type DirectMessageItem, type PublicUser } from "@/lib/api";

const COMMUNITY_SLUG = "mindease-support";

interface ChatLine {
  id: string;
  from_user_id: string;
  body: string;
  created_at: string | null;
}

const members = [
  { name: "Sarah M.", status: "Finding peace through daily meditation", avatar: "S" },
  { name: "Alex R.", status: "One step at a time", avatar: "A" },
  { name: "Jamie L.", status: "Learning to embrace vulnerability", avatar: "J" },
];

function moodBadge(mood: CommunityPost["mood"]) {
  const map: Record<CommunityPost["mood"], { label: string; cls: string }> = {
    stress: { label: "Stress", cls: "bg-peach/15 text-peach" },
    anxiety: { label: "Anxiety", cls: "bg-lavender/15 text-lavender" },
    sadness: { label: "Sadness", cls: "bg-teal/15 text-teal" },
    happiness: { label: "Happiness", cls: "bg-sage/15 text-sage" },
    anger: { label: "Anger", cls: "bg-destructive/10 text-destructive" },
    fear: { label: "Fear", cls: "bg-muted/60 text-foreground" },
    neutrality: { label: "Neutral", cls: "bg-muted/60 text-muted-foreground" },
  };
  return map[mood];
}

const Community = () => {
  useRequireAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const chatScrollRef = useRef<HTMLDivElement>(null);
  const selectedPeerRef = useRef<PublicUser | null>(null);

  const [token] = useState(() => localStorage.getItem("accessToken"));
  const [joinedCommunity, setJoinedCommunity] = useState(false);
  const [loadingJoin, setLoadingJoin] = useState(false);
  const [banner, setBanner] = useState("");
  const [error, setError] = useState("");

  const [searchQ, setSearchQ] = useState("");
  const [searchResults, setSearchResults] = useState<PublicUser[]>([]);
  const [searching, setSearching] = useState(false);
  const [requestingUserId, setRequestingUserId] = useState<string | null>(null);

  const [requestEmail, setRequestEmail] = useState("");
  const [loadingRequest, setLoadingRequest] = useState(false);

  const [selectedPeer, setSelectedPeer] = useState<PublicUser | null>(null);
  const [chatLines, setChatLines] = useState<ChatLine[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [loadingMessages, setLoadingMessages] = useState(false);

  const [likedPostIds, setLikedPostIds] = useState<Set<string>>(() => {
    try {
      const raw = localStorage.getItem("communityLikedPostIds");
      if (!raw) return new Set();
      return new Set(JSON.parse(raw) as string[]);
    } catch {
      return new Set();
    }
  });
  const [commentDraft, setCommentDraft] = useState<Record<string, string>>({});
  const [comments, setComments] = useState<Record<string, string[]>>({});

  const [postText, setPostText] = useState("");
  const [posting, setPosting] = useState(false);

  const { data: feed, refetch: refetchFeed } = useQuery({
    queryKey: ["communityFeed"],
    queryFn: () => api.getCommunityFeed(30),
  });

  const { data: me } = useQuery({
    queryKey: ["me"],
    queryFn: () => api.getMe(),
  });

  const { data: connState, refetch: refetchConnections } = useQuery({
    queryKey: ["connectionState"],
    queryFn: () => api.getConnectionState(),
  });

  const myId = me?.id ?? "";

  useEffect(() => {
    selectedPeerRef.current = selectedPeer;
  }, [selectedPeer]);

  const appendUniqueLines = useCallback((incoming: DirectMessageItem[]) => {
    setChatLines((prev) => {
      const seen = new Set(prev.map((p) => p.id));
      const next = [...prev];
      for (const row of incoming) {
        if (!seen.has(row.id)) {
          seen.add(row.id);
          next.push({
            id: row.id,
            from_user_id: row.from_user_id,
            body: row.body,
            created_at: row.created_at,
          });
        }
      }
      next.sort((a, b) => (a.created_at ?? "").localeCompare(b.created_at ?? ""));
      return next;
    });
  }, []);

  const onWsDm = useCallback(
    (msg: { id: string; from_user_id: string; to_user_id: string; body: string; created_at: string }) => {
      const peer = selectedPeerRef.current;
      if (!peer) return;
      const peerId = peer.id;
      if (msg.from_user_id !== peerId && msg.to_user_id !== peerId) return;
      appendUniqueLines([
        {
          id: msg.id,
          from_user_id: msg.from_user_id,
          to_user_id: msg.to_user_id,
          body: msg.body,
          created_at: msg.created_at,
        },
      ]);
    },
    [appendUniqueLines],
  );

  const { sendDm } = useSocialWebSocket(token, {
    onDm: onWsDm,
    onConnectionStateChanged: () => {
      void queryClient.invalidateQueries({ queryKey: ["connectionState"] });
      void refetchConnections();
    },
    onWsError: (d) => setError(d),
  });

  // Scroll only the chat column — scrollIntoView on a child scrolls the window and causes the whole page to “slide”.
  useLayoutEffect(() => {
    const el = chatScrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [chatLines]);

  useEffect(() => {
    const t = window.setTimeout(() => {
      const q = searchQ.trim();
      if (q.length < 2) {
        setSearchResults([]);
        return;
      }
      setSearching(true);
      setError("");
      api
        .searchUsers(q)
        .then(setSearchResults)
        .catch((err) => {
          setError(err instanceof Error ? err.message : "Search failed");
          setSearchResults([]);
        })
        .finally(() => setSearching(false));
    }, 320);
    return () => window.clearTimeout(t);
  }, [searchQ]);

  useEffect(() => {
    if (!selectedPeer || !myId) {
      setChatLines([]);
      return;
    }
    setLoadingMessages(true);
    setError("");
    api
      .getDirectMessages(selectedPeer.id)
      .then((rows) => {
        setChatLines(
          rows.map((r) => ({
            id: r.id,
            from_user_id: r.from_user_id,
            body: r.body,
            created_at: r.created_at,
          })),
        );
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Could not load messages");
        setChatLines([]);
      })
      .finally(() => setLoadingMessages(false));
  }, [selectedPeer, myId]);

  const handleJoinCommunity = async () => {
    setError("");
    setBanner("");
    setLoadingJoin(true);
    try {
      const res = await api.joinCommunity(COMMUNITY_SLUG);
      setBanner(res.message);
      setJoinedCommunity(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not join community");
    } finally {
      setLoadingJoin(false);
    }
  };

  const sendRequestToEmail = async (email: string) => {
    const e = email.trim().toLowerCase();
    if (!e.includes("@")) {
      setError("Enter a valid email.");
      return;
    }
    setLoadingRequest(true);
    setError("");
    try {
      const res = await api.sendConnectionRequest({ target_user_email: e });
      setBanner(res.message);
      await refetchConnections();
      setRequestEmail("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send request");
    } finally {
      setLoadingRequest(false);
    }
  };

  const sendRequestToUserId = async (u: PublicUser) => {
    setError("");
    setRequestingUserId(u.id);
    try {
      const res = await api.sendConnectionRequest({ target_user_id: u.id });
      setBanner(res.message);
      await refetchConnections();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send request");
    } finally {
      setRequestingUserId(null);
    }
  };

  const accept = async (requestId: string) => {
    setError("");
    try {
      const res = await api.acceptConnection(requestId);
      setBanner(res.message);
      await refetchConnections();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not accept");
    }
  };

  const reject = async (requestId: string) => {
    setError("");
    try {
      const res = await api.rejectConnection(requestId);
      setBanner(res.message);
      await refetchConnections();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update request");
    }
  };

  const openChat = (u: PublicUser) => {
    setSelectedPeer(u);
    setBanner("");
    setError("");
  };

  const sendChat = () => {
    const text = chatInput.trim();
    if (!text || !selectedPeer) return;
    setChatInput("");
    setError("");
    sendDm(selectedPeer.id, text);
  };

  const toggleLike = (postId: string) => {
    setLikedPostIds((prev) => {
      const next = new Set(prev);
      if (next.has(postId)) next.delete(postId);
      else next.add(postId);
      localStorage.setItem("communityLikedPostIds", JSON.stringify(Array.from(next)));
      return next;
    });
  };

  const addComment = async (postId: string) => {
    const text = (commentDraft[postId] ?? "").trim();
    if (!text) return;
    setError("");
    try {
      await api.commentCommunityPost(postId, text);
      setComments((prev) => ({ ...prev, [postId]: [...(prev[postId] ?? []), text] }));
      setCommentDraft((prev) => ({ ...prev, [postId]: "" }));
      await refetchFeed();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not comment");
    }
  };

  const likePost = async (postId: string) => {
    toggleLike(postId);
    try {
      await api.likeCommunityPost(postId);
      await refetchFeed();
    } catch {
      // ignore: client like is still shown; server will sync on refresh
    }
  };

  const submitPost = async () => {
    const text = postText.trim();
    if (text.length < 2) {
      setError("Write a short post (at least 2 characters).");
      return;
    }
    setPosting(true);
    setError("");
    try {
      await api.createCommunityPost(text);
      setPostText("");
      await refetchFeed();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not post");
    } finally {
      setPosting(false);
    }
  };

  const incoming = connState?.incoming_pending ?? [];
  const outgoing = connState?.outgoing_pending ?? [];
  const connections = connState?.connections ?? [];

  return (
    <div className="min-h-screen relative overflow-hidden gradient-bg px-4 py-12">
      <FloatingOrbs />
      <div className="container mx-auto max-w-6xl relative z-10">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl gradient-primary mb-4">
            <Globe className="w-8 h-8 text-primary-foreground" />
          </div>
          <h1 className="text-4xl font-display font-bold text-foreground mb-3">Community</h1>
          <p className="text-muted-foreground max-w-xl mx-auto">
            Join the shared space, send connection requests, and chat in real time once both sides agree to connect.
          </p>
        </motion.div>

        <div className="glass-card-strong p-6 mb-8 space-y-4">
          <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
            <UserPlus className="w-5 h-5 text-primary" />
            Join community (saved to your account)
          </h2>
          <button
            type="button"
            onClick={() => void handleJoinCommunity()}
            disabled={loadingJoin || joinedCommunity}
            className="btn-primary w-full sm:w-auto disabled:opacity-60"
          >
            {loadingJoin ? <Loader2 className="w-4 h-4 animate-spin inline mr-2" /> : null}
            {joinedCommunity ? "Joined" : `Join “${COMMUNITY_SLUG}”`}
          </button>
        </div>

        {banner ? <p className="text-sm text-primary font-medium mb-4 text-center">{banner}</p> : null}
        {error ? <p className="text-sm text-destructive mb-4 text-center">{error}</p> : null}

        <div className="grid lg:grid-cols-2 gap-8 mb-12 min-w-0">
          <Tabs defaultValue="find" className="w-full min-w-0">
            <TabsList className="grid w-full grid-cols-4 h-auto flex-wrap gap-1 bg-muted/60 p-2">
              <TabsTrigger value="find" className="text-xs sm:text-sm">
                Find
              </TabsTrigger>
              <TabsTrigger value="sent" className="text-xs sm:text-sm">
                Sent
              </TabsTrigger>
              <TabsTrigger value="pending" className="text-xs sm:text-sm">
                Pending
              </TabsTrigger>
              <TabsTrigger value="friends" className="text-xs sm:text-sm">
                Connected
              </TabsTrigger>
            </TabsList>

            <TabsContent value="find" className="mt-4 space-y-4">
              <div className="glass-card p-4 space-y-3">
                <label className="text-sm font-medium text-foreground flex items-center gap-2">
                  <Search className="w-4 h-4" />
                  Search registered users
                </label>
                <input
                  value={searchQ}
                  onChange={(e) => setSearchQ(e.target.value)}
                  placeholder="Name or email (min 2 characters)"
                  className="mindease-input w-full"
                />
                {searching ? (
                  <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                ) : (
                  <ul className="space-y-2 max-h-56 overflow-y-auto">
                    {searchResults.map((u) => (
                      <li
                        key={u.id}
                        className="flex items-center justify-between gap-2 rounded-lg border border-border/50 bg-background/40 px-3 py-2"
                      >
                        <div>
                          <div className="font-medium text-foreground">{u.name}</div>
                          <div className="text-xs text-muted-foreground">{u.email_masked}</div>
                        </div>
                        <button
                          type="button"
                          disabled={requestingUserId === u.id || u.id === myId}
                          onClick={() => void sendRequestToUserId(u)}
                          className="btn-ghost text-xs whitespace-nowrap py-1 px-2"
                        >
                          {requestingUserId === u.id ? <Loader2 className="w-3 h-3 animate-spin" /> : "Request"}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="glass-card p-4 space-y-2">
                <p className="text-sm text-muted-foreground">
                  Or invite someone by full email if you already know their MindEase login.
                </p>
                <div className="flex flex-col sm:flex-row gap-2">
                  <input
                    type="email"
                    value={requestEmail}
                    onChange={(e) => setRequestEmail(e.target.value)}
                    placeholder="friend@example.com"
                    className="mindease-input flex-1"
                  />
                  <button
                    type="button"
                    disabled={loadingRequest}
                    onClick={() => void sendRequestToEmail(requestEmail)}
                    className="btn-primary whitespace-nowrap"
                  >
                    {loadingRequest ? <Loader2 className="w-4 h-4 animate-spin" /> : "Send request"}
                  </button>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="sent" className="mt-4 space-y-2">
              <p className="text-sm text-muted-foreground mb-2 flex items-center gap-2">
                <Clock className="w-4 h-4" />
                Waiting for the other person to accept.
              </p>
              {outgoing.length === 0 ? (
                <p className="text-sm text-muted-foreground">No outgoing requests.</p>
              ) : (
                outgoing.map((row) => (
                  <div
                    key={row.request_id}
                    className="glass-card p-4 flex items-center justify-between gap-2"
                  >
                    <div>
                      <div className="font-medium">{row.user.name}</div>
                      <div className="text-xs text-muted-foreground">{row.user.email_masked}</div>
                    </div>
                    <span className="text-xs text-muted-foreground">Pending</span>
                  </div>
                ))
              )}
            </TabsContent>

            <TabsContent value="pending" className="mt-4 space-y-2">
              <p className="text-sm text-muted-foreground mb-2">Accept to unlock real-time chat with this person.</p>
              {incoming.length === 0 ? (
                <p className="text-sm text-muted-foreground">No pending requests.</p>
              ) : (
                incoming.map((row) => (
                  <div
                    key={row.request_id}
                    className="glass-card p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                  >
                    <div>
                      <div className="font-medium">{row.user.name}</div>
                      <div className="text-xs text-muted-foreground">{row.user.email_masked}</div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => void accept(row.request_id)}
                        className="btn-primary text-sm py-2 px-3 flex items-center gap-1"
                      >
                        <Check className="w-4 h-4" /> Accept
                      </button>
                      <button
                        type="button"
                        onClick={() => void reject(row.request_id)}
                        className="btn-ghost text-sm py-2 px-3 flex items-center gap-1"
                      >
                        <X className="w-4 h-4" /> Decline
                      </button>
                    </div>
                  </div>
                ))
              )}
            </TabsContent>

            <TabsContent value="friends" className="mt-4 space-y-2">
              {connections.length === 0 ? (
                <p className="text-sm text-muted-foreground">No accepted connections yet.</p>
              ) : (
                connections.map((row) => (
                  <button
                    key={row.request_id}
                    type="button"
                    onClick={() => openChat(row.user)}
                    className={`w-full text-left glass-card p-4 flex items-center justify-between gap-2 transition-all hover:shadow-md ${
                      selectedPeer?.id === row.user.id ? "ring-2 ring-primary" : ""
                    }`}
                  >
                    <div>
                      <div className="font-medium">{row.user.name}</div>
                      <div className="text-xs text-muted-foreground">{row.user.email_masked}</div>
                    </div>
                    <MessageCircle className="w-5 h-5 text-primary shrink-0" />
                  </button>
                ))
              )}
            </TabsContent>
          </Tabs>

          <div className="glass-card-strong flex flex-col min-h-[420px] min-w-0 overflow-hidden">
            <div className="border-b border-border/50 px-4 py-3 shrink-0">
              <h2 className="font-semibold text-foreground flex items-center gap-2">
                <MessageCircle className="w-5 h-5 text-primary" />
                {selectedPeer ? `Chat with ${selectedPeer.name}` : "Direct messages"}
              </h2>
              <p className="text-xs text-muted-foreground mt-1">
                {selectedPeer
                  ? "Messages are delivered instantly while you are online. History loads from the server."
                  : "Select someone under Connected to start."}
              </p>
            </div>
            <div
              ref={chatScrollRef}
              className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden overscroll-y-contain px-4 py-3 space-y-3"
            >
              {loadingMessages ? (
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground mx-auto mt-8" />
              ) : (
                chatLines.map((line) => {
                  const mine = line.from_user_id === myId;
                  return (
                    <div
                      key={line.id}
                      className={`flex min-w-0 ${mine ? "justify-end" : "justify-start"}`}
                    >
                      <div
                        className={`max-w-[85%] min-w-0 rounded-2xl px-4 py-2 text-sm break-words [overflow-wrap:anywhere] ${
                          mine ? "gradient-primary text-primary-foreground" : "glass-card text-foreground"
                        }`}
                      >
                        {line.body}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
            <div className="border-t border-border/50 p-3 flex gap-2 shrink-0 min-w-0">
              <input
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && sendChat()}
                disabled={!selectedPeer}
                placeholder={selectedPeer ? "Type a message…" : "Pick a connection first"}
                className="mindease-input flex-1 min-w-0 disabled:opacity-50"
              />
              <button
                type="button"
                onClick={sendChat}
                disabled={!selectedPeer || !chatInput.trim()}
                className="btn-primary px-3 disabled:opacity-40"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-10">
          {[
            { icon: Users, label: "Your journey", value: "Together" },
            { icon: MessageCircle, label: "Support", value: "Live chat" },
            { icon: Heart, label: "Care", value: "Always" },
          ].map(({ icon: Icon, label, value }, i) => (
            <motion.div
              key={label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 + i * 0.08 }}
              className="glass-card p-6 text-center"
            >
              <Icon className="w-6 h-6 text-primary mx-auto mb-2" />
              <div className="text-xl font-bold text-foreground">{value}</div>
              <div className="text-sm text-muted-foreground">{label}</div>
            </motion.div>
          ))}
        </div>

        <div className="space-y-4 mb-10">
          <h2 className="text-xl font-display font-semibold text-foreground">Community voices</h2>
          {members.map((m, i) => (
            <motion.div
              key={m.name}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.25 + i * 0.06 }}
              className="glass-card p-5 flex items-center gap-4"
            >
              <div className="w-12 h-12 rounded-xl gradient-primary flex items-center justify-center text-primary-foreground font-bold">
                {m.avatar}
              </div>
              <div className="flex-1">
                <div className="font-semibold text-foreground">{m.name}</div>
                <div className="text-sm text-muted-foreground">{m.status}</div>
              </div>
            </motion.div>
          ))}
        </div>

        <div className="space-y-4 mb-10">
          <h2 className="text-xl font-display font-semibold text-foreground">Random talks</h2>
          <p className="text-sm text-muted-foreground">
            Share something. The AI replies automatically using the same engine as the main AI chat.
          </p>
          <div className="glass-card p-5 space-y-3">
            <textarea
              value={postText}
              onChange={(e) => setPostText(e.target.value)}
              placeholder="Write a post or a question…"
              rows={3}
              className="mindease-input resize-none"
            />
            <div className="flex justify-end">
              <button type="button" onClick={() => void submitPost()} disabled={posting} className="btn-primary">
                {posting ? <Loader2 className="w-4 h-4 animate-spin inline mr-2" /> : null}
                Post
              </button>
            </div>
          </div>
          <div className="space-y-3">
            {(feed?.items ?? []).map((p) => {
              const badge = moodBadge(p.mood);
              const liked = likedPostIds.has(p.id);
              return (
                <div key={p.id} className="glass-card p-5 space-y-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs px-2 py-1 rounded-full ${badge.cls}`}>{badge.label}</span>
                      <span className="text-xs text-muted-foreground">
                        {new Date(p.created_at).toLocaleString()}
                      </span>
                    </div>
                    <button type="button" onClick={() => void likePost(p.id)} className="btn-ghost text-xs py-1 px-2">
                      {liked ? `Liked (${p.likes})` : `Like (${p.likes})`}
                    </button>
                  </div>
                  <p className="text-sm text-foreground leading-relaxed">{p.text}</p>
                  <div className="rounded-xl border border-border/40 bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
                    <span className="font-medium text-foreground/80">AI: </span>
                    {p.ai_reply}
                  </div>

                  <div className="flex flex-col sm:flex-row gap-2">
                    <input
                      value={commentDraft[p.id] ?? ""}
                      onChange={(e) => setCommentDraft((prev) => ({ ...prev, [p.id]: e.target.value }))}
                      placeholder="Add a supportive comment…"
                      className="mindease-input flex-1"
                      onKeyDown={(e) => e.key === "Enter" && void addComment(p.id)}
                    />
                    <button type="button" onClick={() => void addComment(p.id)} className="btn-primary whitespace-nowrap">
                      Comment
                    </button>
                  </div>

                  {(p.comments?.length || (comments[p.id] ?? []).length) ? (
                    <div className="space-y-2 pt-2 border-t border-border/40">
                      {p.comments?.map((c, idx) => (
                        <div key={`${p.id}-c-${idx}`} className="text-sm text-muted-foreground">
                          <span className="text-foreground/80 font-medium">Comment:</span> {c}
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        </div>

        <div className="text-center">
          <button type="button" onClick={() => navigate("/thank-you")} className="btn-primary">
            Complete Journey <ArrowRight className="w-4 h-4 inline ml-2" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default Community;
