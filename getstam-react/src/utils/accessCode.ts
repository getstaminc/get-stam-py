/** User-facing message for an access-code redemption error code from the API. */
export const accessCodeErrorMessage = (error?: string): string =>
  error === "already_redeemed" ? "You've already redeemed an access code."
    : error === "code_fully_redeemed" ? "This code has reached its redemption limit."
    : error === "expired_code" ? "This code has expired."
    : "That code isn't valid.";
