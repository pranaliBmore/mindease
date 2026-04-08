const FloatingOrbs = () => (
  <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
    <div className="floating-orb w-72 h-72 bg-teal top-10 -left-20" style={{ animationDelay: '0s' }} />
    <div className="floating-orb w-96 h-96 bg-peach top-1/3 right-0" style={{ animationDelay: '3s' }} />
    <div className="floating-orb w-64 h-64 bg-sage bottom-20 left-1/3" style={{ animationDelay: '5s' }} />
    <div className="floating-orb w-48 h-48 bg-lavender bottom-1/4 right-1/4" style={{ animationDelay: '2s' }} />
  </div>
);

export default FloatingOrbs;
