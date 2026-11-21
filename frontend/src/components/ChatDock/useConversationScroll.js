import { useLayoutEffect, useRef, useState } from 'react';

const FOLLOW_THRESHOLD = 24;

export function useConversationScroll(scrollRef, sessionId, messages, isLoading, activeView) {
  const followingRef = useRef(true);
  const previousSessionRef = useRef(sessionId);
  const [isFollowing, setIsFollowing] = useState(true);

  const onScroll = () => {
    const element = scrollRef.current;
    if (!element) return;
    const distanceToBottom = element.scrollHeight - element.clientHeight - element.scrollTop;
    const next = distanceToBottom <= FOLLOW_THRESHOLD;
    followingRef.current = next;
    setIsFollowing(next);
  };

  const jumpToLatest = () => {
    const element = scrollRef.current;
    if (!element) return;
    followingRef.current = true;
    setIsFollowing(true);
    element.scrollTo({ top: element.scrollHeight, behavior: 'smooth' });
  };

  useLayoutEffect(() => {
    const element = scrollRef.current;
    if (!element) return;
    if (previousSessionRef.current !== sessionId) {
      previousSessionRef.current = sessionId;
      followingRef.current = true;
      setIsFollowing(true);
    }
    if (followingRef.current) element.scrollTop = element.scrollHeight;
  }, [scrollRef, sessionId, messages, isLoading, activeView]);

  return { isFollowing, onScroll, jumpToLatest };
}
