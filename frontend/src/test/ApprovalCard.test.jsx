import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ApprovalCard from '../components/ApprovalCard/ApprovalCard';

describe('ApprovalCard Component', () => {
  const baseProps = {
    approvalId: 'test-app-1',
    toolName: 'notes_reminders_create',
    arguments: { text: 'Buy groceries' },
    diff: {},
    dangerousParams: [],
    warnings: ['Tool requires operator approval.'],
    riskLevel: 'high',
    isTainted: true,
  };

  it('renders risk badges, taint banner, and arguments', () => {
    render(<ApprovalCard {...baseProps} />);
    expect(screen.getByText(/HIGH RISK/i)).toBeInTheDocument();
    expect(screen.getByText(/UNTRUSTED \(Tainted\)/i)).toBeInTheDocument();
    expect(screen.getByText('notes_reminders_create')).toBeInTheDocument();
    expect(screen.getByText('Buy groceries')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Approve Action/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Deny/i })).toBeInTheDocument();
  });

  it('does not prematurely mark decided when approve button is clicked', () => {
    const onApprove = vi.fn();
    render(<ApprovalCard {...baseProps} onApprove={onApprove} status="pending" />);

    const approveBtn = screen.getByRole('button', { name: /Approve Action/i });
    fireEvent.click(approveBtn);

    expect(onApprove).toHaveBeenCalledWith('test-app-1');
    // Still shows buttons because server has not confirmed yet!
    expect(screen.getByRole('button', { name: /Approve Action/i })).toBeInTheDocument();
  });

  it('disables buttons when in submitting state', () => {
    render(<ApprovalCard {...baseProps} status="submitting" />);
    const approveBtn = screen.getByRole('button', { name: /Submitting.../i });
    const denyBtn = screen.getByRole('button', { name: /Deny/i });

    expect(approveBtn).toBeDisabled();
    expect(denyBtn).toBeDisabled();
  });

  it('displays confirmed approved state when server confirms approval', () => {
    render(<ApprovalCard {...baseProps} status="approved" />);
    expect(screen.getByText(/Action Approved by Operator/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Approve Action/i })).not.toBeInTheDocument();
  });

  it('displays confirmed denied state when server confirms denial', () => {
    render(<ApprovalCard {...baseProps} status="denied" />);
    expect(screen.getByText(/Action Denied & Blocked/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Approve Action/i })).not.toBeInTheDocument();
  });

  it('displays expired status when approval expires', () => {
    render(<ApprovalCard {...baseProps} status="expired" />);
    expect(screen.getByText(/Approval Expired or Unavailable/i)).toBeInTheDocument();
  });

  it('displays failure message and keeps retry/deny controls available on failure', () => {
    const onApprove = vi.fn();
    const onDeny = vi.fn();
    render(
      <ApprovalCard
        {...baseProps}
        status="failed"
        errorMessage="Network timeout connecting to server"
        onApprove={onApprove}
        onDeny={onDeny}
      />
    );

    expect(screen.getByText(/Submission failed: Network timeout connecting to server/i)).toBeInTheDocument();
    const retryBtn = screen.getByRole('button', { name: /Retry Approve/i });
    const denyBtn = screen.getByRole('button', { name: /Deny/i });

    expect(retryBtn).toBeEnabled();
    expect(denyBtn).toBeEnabled();

    fireEvent.click(retryBtn);
    expect(onApprove).toHaveBeenCalledWith('test-app-1');

    fireEvent.click(denyBtn);
    expect(onDeny).toHaveBeenCalledWith('test-app-1');
  });
});
