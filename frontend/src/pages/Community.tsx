import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
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
  HeartHandshake,
  Compass,
  Sparkles,
} from "lucide-react";
import Avatar from "@/components/Avatar";
import { useSocialWebSocket } from "@/hooks/useSocialWebSocket";
import { api, type CommunityPost, type DirectMessageItem, type PublicUser } from "@/lib/api";

const COMMUNITY_SLUG = "mindease-support";

interface ChatLine {
  id: string;
  from_user_id: string;
  body: string;
  created_at: string | null;
}

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
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const chatScrollRef = useRef<HTMLDivElement>(null);
  const selectedPeerRef = useRef<PublicUser | null>(null);

  const [token] = useState(() => localStorage.getItem("accessToken"));
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

  const [postText, setPostText] = useState("");
  const [posting, setPosting] = useState(false);

  const [unreadPeerIds, setUnreadPeerIds] = useState<Set<string>>(new Set());

  const requestedTab = (location.state as { tab?: string } | null)?.tab;
  const [activeTab, setActiveTab] = useState(
    requestedTab === "sent" || requestedTab === "pending" || requestedTab === "friends" ? requestedTab : "discover",
  );

  const { data: feed, refetch: refetchFeed } = useQuery({
    queryKey: ["communityFeed"],
    queryFn: () => api.getCommunityFeed(30),
  });

  const { data: me } = useQuery({
    queryKey: ["me"],
    queryFn: () => api.getMe(),
  });

  const { data: connState, isLoading: loadingConnections } = useQuery({
    queryKey: ["connectionState"],
    queryFn: () => api.getConnectionState(),
  });

  const { data: discoverUsers, isLoading: loadingDiscover } = useQuery({
    queryKey: ["discoverUsers"],
    queryFn: () => api.discoverUsers(24),
  });

  const { data: communityDetails } = useQuery({
    queryKey: ["communityDetails", COMMUNITY_SLUG],
    queryFn: () => api.getCommunityDetails(COMMUNITY_SLUG),
  });

  // Derived from the account, not local state - so it survives a reload instead of
  // forgetting you joined the moment you refresh the page.
  const joinedCommunity = me?.communities?.includes(COMMUNITY_SLUG) ?? false;

  const myId = me?.id ?? "";

  // Single source of truth for "something about who's pending/connected/discoverable
  // changed" - every mutation (send/accept/reject) and every WS push routes through
  // this instead of hand-picking which queries to refetch, so a case can't be missed.
  const refreshSocialState = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ["connectionState"] });
    void queryClient.invalidateQueries({ queryKey: ["discoverUsers"] });
  }, [queryClient]);

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
      const isOpenConversation = !!peer && (msg.from_user_id === peer.id || msg.to_user_id === peer.id);
      if (!isOpenConversation) {
        // Message belongs to a conversation that isn't open right now - still surface it
        // as an unread marker instead of silently dropping it.
        if (msg.from_user_id !== myId) {
          setUnreadPeerIds((prev) => {
            if (prev.has(msg.from_user_id)) return prev;
            const next = new Set(prev);
            next.add(msg.from_user_id);
            return next;
          });
        }
        return;
      }
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
    [appendUniqueLines, myId],
  );

  const { sendDm } = useSocialWebSocket(token, {
    onDm: onWsDm,
    onConnectionStateChanged: refreshSocialState,
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
      void queryClient.invalidateQueries({ queryKey: ["me"] });
      void queryClient.invalidateQueries({ queryKey: ["communityDetails", COMMUNITY_SLUG] });
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
      refreshSocialState();
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
      refreshSocialState();
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
      refreshSocialState();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not accept");
    }
  };

  const reject = async (requestId: string) => {
    setError("");
    try {
      const res = await api.rejectConnection(requestId);
      setBanner(res.message);
      refreshSocialState();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update request");
    }
  };

  const handleTabChange = (value: string) => {
    setActiveTab(value);
    // Chat panel is a persistent side-column, not tied to the tabs - but leaving it
    // open while browsing Discover/Search/Sent/Pending reads as "stuck". Close it when
    // navigating away from Connected.
    if (value !== "friends") {
      setSelectedPeer(null);
    }
  };

  const openChat = (u: PublicUser) => {
    setSelectedPeer(u);
    setBanner("");
    setError("");
    setUnreadPeerIds((prev) => {
      if (!prev.has(u.id)) return prev;
      const next = new Set(prev);
      next.delete(u.id);
      return next;
    });
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

  const connectedIds = useMemo(() => new Set(connections.map((row) => row.user.id)), [connections]);
  const outgoingIds = useMemo(() => new Set(outgoing.map((row) => row.user.id)), [outgoing]);
  const incomingIds = useMemo(() => new Set(incoming.map((row) => row.user.id)), [incoming]);
  const hasUnread = unreadPeerIds.size > 0;

  const relationshipLabel = (userId: string): string | null => {
    if (connectedIds.has(userId)) return "Connected";
    if (outgoingIds.has(userId)) return "Pending";
    if (incomingIds.has(userId)) return "Wants to connect";
    return null;
  };

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

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          onClick={() => navigate("/match")}
          className="glass-card-strong p-6 mb-8 cursor-pointer group hover:shadow-elevated transition-all duration-500 hover:-translate-y-1 flex items-center gap-5"
        >
          <div className="w-14 h-14 rounded-2xl gradient-primary flex items-center justify-center shrink-0 group-hover:scale-110 transition-transform">
            <HeartHandshake className="w-7 h-7 text-primary-foreground" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-lg font-display font-semibold text-foreground mb-1">
              Don't know anyone here yet? Find a match
            </h2>
            <p className="text-sm text-muted-foreground">
              Answer a few quick questions and we'll anonymously pair you with someone else going through something
              similar, to talk and help each other feel better.
            </p>
          </div>
          <ArrowRight className="w-5 h-5 text-primary shrink-0 group-hover:translate-x-1 transition-transform" />
        </motion.div>

        <div className="glass-card-strong p-6 mb-8 space-y-4">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
                <UserPlus className="w-5 h-5 text-primary" />
                {joinedCommunity ? "You're a member" : "Join the community"}
              </h2>
              <p className="text-sm text-muted-foreground mt-1">
                {joinedCommunity
                  ? "The Community Wall below is unlocked - post, like, and see what others are going through."
                  : "Unlocks the Community Wall: post what's on your mind and see real posts from other members."}
              </p>
            </div>
            {communityDetails ? (
              <span className="inline-flex items-center gap-1.5 text-sm font-medium text-primary bg-primary/10 px-3 py-1.5 rounded-full shrink-0">
                <Users className="w-4 h-4" />
                {communityDetails.member_count} {communityDetails.member_count === 1 ? "member" : "members"}
              </span>
            ) : null}
          </div>
          {!joinedCommunity ? (
            <button
              type="button"
              onClick={() => void handleJoinCommunity()}
              disabled={loadingJoin}
              className="btn-primary w-full sm:w-auto disabled:opacity-60"
            >
              {loadingJoin ? <Loader2 className="w-4 h-4 animate-spin inline mr-2" /> : null}
              Join community
            </button>
          ) : null}
        </div>

        {banner ? <p className="text-sm text-primary font-medium mb-4 text-center">{banner}</p> : null}
        {error ? <p className="text-sm text-destructive mb-4 text-center">{error}</p> : null}

        <div className="grid lg:grid-cols-2 gap-8 mb-12 min-w-0">
          <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full min-w-0">
            <TabsList className="grid w-full grid-cols-5 h-auto flex-wrap gap-1 bg-muted/60 p-2">
              <TabsTrigger value="discover" className="text-xs sm:text-sm">
                Discover
              </TabsTrigger>
              <TabsTrigger value="find" className="text-xs sm:text-sm">
                Search
              </TabsTrigger>
              <TabsTrigger value="sent" className="text-xs sm:text-sm">
                Sent
              </TabsTrigger>
              <TabsTrigger value="pending" className="text-xs sm:text-sm relative">
                Pending
                {incoming.length > 0 ? (
                  <span className="absolute -top-1.5 -right-1.5 min-w-[1.1rem] h-[1.1rem] px-1 rounded-full bg-destructive text-[10px] leading-[1.1rem] text-destructive-foreground font-bold text-center">
                    {incoming.length}
                  </span>
                ) : null}
              </TabsTrigger>
              <TabsTrigger value="friends" className="text-xs sm:text-sm relative">
                Connected
                {hasUnread ? (
                  <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-destructive" />
                ) : null}
              </TabsTrigger>
            </TabsList>

            <TabsContent value="discover" className="mt-4 space-y-3">
              <p className="text-sm text-muted-foreground flex items-center gap-2">
                <Compass className="w-4 h-4" />
                Browse real people here - no need to already know their name or email.
              </p>
              {loadingDiscover ? (
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground mx-auto mt-4" />
              ) : (discoverUsers ?? []).length === 0 ? (
                <div className="glass-card p-5 space-y-3 text-center">
                  <p className="text-sm text-muted-foreground">
                    No one new to discover right now - check back soon, or let us pair you with someone instead.
                  </p>
                  <button type="button" onClick={() => navigate("/match")} className="btn-ghost text-sm">
                    Try Find a Match
                  </button>
                </div>
              ) : (
                <ul className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
                  {(discoverUsers ?? []).map((u) => {
                    const badge = u.mood ? moodBadge(u.mood as CommunityPost["mood"]) : null;
                    return (
                      <li key={u.id} className="glass-card p-4 flex items-center gap-3">
                        <Avatar name={u.name} avatarUrl={u.avatar_url} />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-medium text-foreground">{u.name}</span>
                            {badge ? (
                              <span className={`text-[10px] px-2 py-0.5 rounded-full ${badge.cls} flex items-center gap-1`}>
                                {u.shares_your_mood ? <Sparkles className="w-2.5 h-2.5" /> : null}
                                {u.shares_your_mood ? `Feeling ${badge.label.toLowerCase()} too` : badge.label}
                              </span>
                            ) : null}
                          </div>
                          <p className="text-xs text-muted-foreground truncate">
                            {u.bio || "No bio yet"}
                          </p>
                        </div>
                        <button
                          type="button"
                          disabled={requestingUserId === u.id}
                          onClick={() => void sendRequestToUserId(u)}
                          className="btn-ghost text-xs whitespace-nowrap py-1 px-2 shrink-0"
                        >
                          {requestingUserId === u.id ? <Loader2 className="w-3 h-3 animate-spin" /> : "Connect"}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </TabsContent>

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
                    {searchResults.map((u) => {
                      const existingStatus = relationshipLabel(u.id);
                      return (
                      <li
                        key={u.id}
                        className="flex items-center gap-3 rounded-lg border border-border/50 bg-background/40 px-3 py-2"
                      >
                        <Avatar name={u.name} avatarUrl={u.avatar_url} size="sm" />
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-foreground truncate">{u.name}</div>
                          <div className="text-xs text-muted-foreground truncate">{u.email_masked}</div>
                        </div>
                        {existingStatus ? (
                          <span className="text-xs text-muted-foreground whitespace-nowrap py-1 px-2">
                            {existingStatus}
                          </span>
                        ) : (
                          <button
                            type="button"
                            disabled={requestingUserId === u.id || u.id === myId}
                            onClick={() => void sendRequestToUserId(u)}
                            className="btn-ghost text-xs whitespace-nowrap py-1 px-2"
                          >
                            {requestingUserId === u.id ? <Loader2 className="w-3 h-3 animate-spin" /> : "Request"}
                          </button>
                        )}
                      </li>
                      );
                    })}
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
              {loadingConnections ? (
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground mx-auto mt-4" />
              ) : outgoing.length === 0 ? (
                <p className="text-sm text-muted-foreground">No outgoing requests.</p>
              ) : (
                outgoing.map((row) => (
                  <div key={row.request_id} className="glass-card p-4 flex items-center gap-3">
                    <Avatar name={row.user.name} avatarUrl={row.user.avatar_url} size="sm" />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate">{row.user.name}</div>
                      <div className="text-xs text-muted-foreground truncate">{row.user.email_masked}</div>
                    </div>
                    <span className="text-xs text-muted-foreground shrink-0">Pending</span>
                  </div>
                ))
              )}
            </TabsContent>

            <TabsContent value="pending" className="mt-4 space-y-2">
              <p className="text-sm text-muted-foreground mb-2">Accept to unlock real-time chat with this person.</p>
              {loadingConnections ? (
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground mx-auto mt-4" />
              ) : incoming.length === 0 ? (
                <p className="text-sm text-muted-foreground">No pending requests.</p>
              ) : (
                incoming.map((row) => (
                  <div
                    key={row.request_id}
                    className="glass-card p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <Avatar name={row.user.name} avatarUrl={row.user.avatar_url} size="sm" />
                      <div className="min-w-0">
                        <div className="font-medium truncate">{row.user.name}</div>
                        <div className="text-xs text-muted-foreground truncate">{row.user.email_masked}</div>
                      </div>
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
              {loadingConnections ? (
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground mx-auto mt-4" />
              ) : connections.length === 0 ? (
                <p className="text-sm text-muted-foreground">No accepted connections yet.</p>
              ) : (
                connections.map((row) => {
                  const unread = unreadPeerIds.has(row.user.id);
                  return (
                    <button
                      key={row.request_id}
                      type="button"
                      onClick={() => openChat(row.user)}
                      className={`w-full text-left glass-card p-4 flex items-center gap-3 transition-all hover:shadow-md ${
                        selectedPeer?.id === row.user.id ? "ring-2 ring-primary" : ""
                      }`}
                    >
                      <Avatar name={row.user.name} avatarUrl={row.user.avatar_url} size="sm" />
                      <div className="flex-1 min-w-0">
                        <div className={`truncate ${unread ? "font-bold text-foreground" : "font-medium"}`}>
                          {row.user.name}
                        </div>
                        <div className="text-xs text-muted-foreground truncate">{row.user.email_masked}</div>
                      </div>
                      {unread ? (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-destructive text-destructive-foreground font-bold shrink-0">
                          New
                        </span>
                      ) : null}
                      <MessageCircle className="w-5 h-5 text-primary shrink-0" />
                    </button>
                  );
                })
              )}
            </TabsContent>
          </Tabs>

          <div className="glass-card-strong flex flex-col min-h-[420px] min-w-0 overflow-hidden">
            <div className="border-b border-border/50 px-4 py-3 shrink-0 flex items-center gap-3">
              {selectedPeer ? <Avatar name={selectedPeer.name} avatarUrl={selectedPeer.avatar_url} size="sm" /> : null}
              <div className="min-w-0">
                <h2 className="font-semibold text-foreground flex items-center gap-2 truncate">
                  {!selectedPeer ? <MessageCircle className="w-5 h-5 text-primary shrink-0" /> : null}
                  {selectedPeer ? `Chat with ${selectedPeer.name}` : "Direct messages"}
                </h2>
                <p className="text-xs text-muted-foreground mt-1">
                  {selectedPeer
                    ? "Messages are delivered instantly while you are online. History loads from the server."
                    : "Select someone under Connected to start."}
                </p>
              </div>
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
            { icon: Users, label: "Members here", value: communityDetails ? String(communityDetails.member_count) : "…" },
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
          <h2 className="text-xl font-display font-semibold text-foreground">Community Wall</h2>
          {!joinedCommunity ? (
            <div className="glass-card-strong p-8 text-center space-y-3">
              <UserPlus className="w-8 h-8 text-primary mx-auto" />
              <h3 className="font-semibold text-foreground">Join to unlock the wall</h3>
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                Posts from other members and your own space to share what's on your mind are reserved for
                community members. Join above - it takes one click - to see and post here.
              </p>
            </div>
          ) : (
            <>
              <p className="text-sm text-muted-foreground">
                Share what's on your mind. Other people here can reply and support you directly - MindEase also
                chimes in right away so you're never met with silence.
              </p>
              <div className="glass-card p-5 space-y-3">
                <textarea
                  value={postText}
                  onChange={(e) => setPostText(e.target.value)}
                  placeholder="What's going on with you today?"
                  rows={3}
                  className="mindease-input resize-none"
                />
                <div className="flex justify-end">
                  <button type="button" onClick={() => void submitPost()} disabled={posting} className="btn-primary">
                    {posting ? <Loader2 className="w-4 h-4 animate-spin inline mr-2" /> : null}
                    Share
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
                    <div className="flex items-center gap-2 min-w-0">
                      <Avatar name={p.author.name} avatarUrl={p.author.avatar_url} size="sm" />
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-foreground truncate">{p.author.name}</div>
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] px-2 py-0.5 rounded-full ${badge.cls}`}>{badge.label}</span>
                          <span className="text-xs text-muted-foreground">
                            {new Date(p.created_at).toLocaleString()}
                          </span>
                        </div>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => void likePost(p.id)}
                      className="btn-ghost text-xs py-1 px-2 shrink-0"
                    >
                      {liked ? `Liked (${p.likes})` : `Like (${p.likes})`}
                    </button>
                  </div>
                  <p className="text-sm text-foreground leading-relaxed">{p.text}</p>
                  <div className="rounded-xl border border-border/40 bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
                    <span className="font-medium text-foreground/80">MindEase: </span>
                    {p.ai_reply}
                  </div>
                </div>
              );
            })}
              </div>
            </>
          )}
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
