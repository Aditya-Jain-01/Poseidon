import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';
import TrajectoryView from '../components/TrajectoryView/TrajectoryView';

vi.mock('../api/agents', () => ({ fetchTrajectory: vi.fn() }));
afterEach(cleanup);

const messages = [
  { id: '1', role: 'user', content: 'This is Burchat, I like to larp as my hobby', timestamp: '2026-10-18T12:00:00Z' },
  { id: '2', role: 'agent', content: `Hello Burchat! ${'Some background information. '.repeat(8)}LARPing sounds fun.`, timestamp: '2026-10-18T12:00:01Z' },
  { id: '3', role: 'user', content: 'An unrelated question', timestamp: '2026-10-18T12:00:02Z' },
];

describe('Trajectory keyword search', () => {
  it.each(['burchat larp', 'larp burchat', '  BURCHAT   LARP  ', 'burchat\tlarp', 'burchat'])('matches separated keywords: %s', (query) => {
    const { container } = render(<TrajectoryView messages={messages} />);
    fireEvent.change(screen.getByPlaceholderText('Search'), { target: { value: query } });
    const rows = container.querySelectorAll('.ledger-event-row');
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent('This is Burchat');
    // The assistant match requires searching its full result beyond the preview.
    expect(rows[1]).toHaveTextContent('Hello Burchat!');
  });

  it('requires all terms within the same event', () => {
    const { container } = render(<TrajectoryView messages={messages} />);
    fireEvent.change(screen.getByPlaceholderText('Search'), { target: { value: 'burchat unrelated' } });
    expect(container.querySelectorAll('.ledger-event-row')).toHaveLength(0);
  });

  it('matches terms across event fields', () => {
    const { container } = render(<TrajectoryView messages={messages} />);
    fireEvent.change(screen.getByPlaceholderText('Search'), { target: { value: 'user larp' } });
    expect(container.querySelectorAll('.ledger-event-row')).toHaveLength(1);
  });

  it('restores all events for whitespace-only or cleared search', () => {
    const { container } = render(<TrajectoryView messages={messages} />);
    for (const query of ['missing', '   ', '']) {
      fireEvent.change(screen.getByPlaceholderText('Search'), { target: { value: query } });
      expect(container.querySelectorAll('.ledger-event-row')).toHaveLength(query === 'missing' ? 0 : 3);
    }
  });
});
