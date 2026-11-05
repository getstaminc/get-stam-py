"""Pro-plan gate on the trends endpoints' min trend length.

Extended trend filters are a Pro feature: free and anonymous callers are clamped
to 5+ (7+ for college, whose much larger daily slates make 7+ the useful default
and what the home page requests). Cache keys must use the CLAMPED value, not the
raw requested one — otherwise a free-tier request for minTrendLength=10 would
populate the shared cache under "...:m10" with clamped results, which would then
be served to the next caller requesting m10, including a legitimate Pro user.
"""

from ...services.auth_service import AuthService
from ...utils.auth_helpers import get_current_user_optional

FREE_MAX_MIN_TREND_LENGTH = 5
PRO_MAX_MIN_TREND_LENGTH = 10
# Sports whose free tier goes further. Mirrored by FREE_MAX_BY_SPORT in GamesWithTrends.tsx.
FREE_MAX_BY_SPORT = {'ncaaf': 7, 'ncaab': 7}


def effective_max_min_trend_length(sport=None) -> int:
    """Max min-trend-length the requesting user is allowed, based on their plan."""
    user = get_current_user_optional()
    if AuthService.effective_plan(user) == 'pro':
        return PRO_MAX_MIN_TREND_LENGTH
    return FREE_MAX_BY_SPORT.get(sport, FREE_MAX_MIN_TREND_LENGTH)


def gated_min_trend_length(requested, sport=None) -> int:
    """Clamp a requested min trend length to what the requesting user's plan allows."""
    return min(int(requested), effective_max_min_trend_length(sport))
