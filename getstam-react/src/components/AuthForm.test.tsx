import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AuthForm from './AuthForm';

const mockRequestCode = jest.fn();
const mockVerifyCode = jest.fn();
jest.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ requestCode: mockRequestCode, verifyCode: mockVerifyCode }),
}));

async function signUpWithAccessCode(props: Partial<React.ComponentProps<typeof AuthForm>> = {}) {
  const onClose = jest.fn();
  render(<AuthForm onClose={onClose} defaultMode="signup" {...props} />);
  await userEvent.click(screen.getByText('Have an access code?'));
  await userEvent.type(screen.getByLabelText('Access code'), 'steph2026');
  await userEvent.click(screen.getByRole('button', { name: 'Continue' }));
  expect(screen.getByText('STEPH2026')).toBeInTheDocument();
  await userEvent.type(screen.getByLabelText(/email/i), 'a@example.com');
  await userEvent.click(screen.getByRole('checkbox'));
  await userEvent.click(screen.getByRole('button', { name: /send code/i }));
  await userEvent.type(await screen.findByLabelText(/6-digit code/i), '123456');
  await userEvent.click(screen.getByRole('button', { name: /verify/i }));
  return { onClose };
}

describe('AuthForm access codes', () => {
  beforeEach(() => {
    mockRequestCode.mockReset().mockResolvedValue({ success: true });
    mockVerifyCode.mockReset();
  });

  it('signs up without a trial intent and sends the code along at verification', async () => {
    mockVerifyCode.mockResolvedValue({ success: true });
    const { onClose } = await signUpWithAccessCode();
    // intent null → the server won't start Checkout
    expect(mockRequestCode).toHaveBeenCalledWith('a@example.com', null, false);
    expect(mockVerifyCode).toHaveBeenCalledWith('a@example.com', '123456', 'steph2026');
    await waitFor(() => expect(onClose).toHaveBeenCalled());
  });

  it('reports a code that could not be redeemed instead of closing', async () => {
    mockVerifyCode.mockResolvedValue({ success: true, accessCodeError: 'code_fully_redeemed' });
    const onAccessCodeError = jest.fn();
    const { onClose } = await signUpWithAccessCode({ onAccessCodeError });
    await waitFor(() => expect(onAccessCodeError).toHaveBeenCalledWith(expect.stringMatching(/reached its redemption limit/)));
    expect(onClose).not.toHaveBeenCalled();
  });
});
