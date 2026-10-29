import { useEffect } from "react";
import { useLocation } from "react-router-dom";

// React Router's client-side navigation doesn't reset scroll position the way
// a full page load does, so clicking a link while scrolled down on one page
// lands at that same scroll offset on the next page (e.g. "Game Details"
// links from the home page's trend cards opening mid-page, near "More
// trends", instead of at the top).
const ScrollToTop: React.FC = () => {
  const { pathname, search } = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname, search]);

  return null;
};

export default ScrollToTop;
