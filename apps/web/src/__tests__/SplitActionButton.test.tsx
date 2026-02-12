/**
 * @vitest-environment jsdom
 */

import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { SplitActionButton } from '../components/SplitActionButton';

function createActions(overrides: { onClick1?: () => void; onClick2?: () => void } = {}) {
  return [
    {
      key: 'send',
      label: '送信',
      icon: <span data-testid="send-icon">S</span>,
      onClick: overrides.onClick1 ?? vi.fn(),
    },
    {
      key: 'draft',
      label: '下書き',
      icon: <span data-testid="draft-icon">D</span>,
      onClick: overrides.onClick2 ?? vi.fn(),
    },
  ];
}

describe('SplitActionButton', () => {
  afterEach(() => {
    cleanup();
  });

  it('デフォルトで最初のアクション（送信）がメインボタンに表示される', () => {
    const actions = createActions();
    render(<SplitActionButton actions={actions} />);

    const mainButton = screen.getByRole('button', { name: /送信/ });
    expect(mainButton).toBeInTheDocument();
    expect(screen.getByTestId('send-icon')).toBeInTheDocument();
  });

  it('メインボタンクリックで選択中のアクションのonClickが呼ばれる', async () => {
    const onClick1 = vi.fn();
    const actions = createActions({ onClick1 });
    const user = userEvent.setup();
    render(<SplitActionButton actions={actions} />);

    await user.click(screen.getByRole('button', { name: /送信/ }));

    expect(onClick1).toHaveBeenCalledTimes(1);
  });

  it('ドロップダウントグルクリックでメニューが表示される', async () => {
    const actions = createActions();
    const user = userEvent.setup();
    render(<SplitActionButton actions={actions} />);

    const toggle = screen.getByRole('button', { name: /選択肢を開く/ });
    await user.click(toggle);

    expect(screen.getByRole('menu')).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: /送信/ })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: /下書き/ })).toBeInTheDocument();
  });

  it('メニューから「下書き」を選択するとメインボタンが「下書き」に変わる', async () => {
    const actions = createActions();
    const user = userEvent.setup();
    render(<SplitActionButton actions={actions} />);

    // メニューを開く
    await user.click(screen.getByRole('button', { name: /選択肢を開く/ }));
    // 下書きを選択
    await user.click(screen.getByRole('menuitem', { name: /下書き/ }));

    // メインボタンが「下書き」に変わる
    const mainButton = screen.getByRole('button', { name: /下書き/ });
    expect(mainButton).toBeInTheDocument();
    expect(screen.getByTestId('draft-icon')).toBeInTheDocument();
    // メニューが閉じる
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  });

  it('メニューアイテム選択時にonClickは呼ばれない（メインボタンクリックで実行）', async () => {
    const onClick2 = vi.fn();
    const actions = createActions({ onClick2 });
    const user = userEvent.setup();
    render(<SplitActionButton actions={actions} />);

    await user.click(screen.getByRole('button', { name: /選択肢を開く/ }));
    await user.click(screen.getByRole('menuitem', { name: /下書き/ }));

    expect(onClick2).not.toHaveBeenCalled();
  });

  it('メニュー外クリックでメニューが閉じる', async () => {
    const actions = createActions();
    const user = userEvent.setup();
    render(
      <div>
        <span data-testid="outside">outside</span>
        <SplitActionButton actions={actions} />
      </div>
    );

    // メニューを開く
    await user.click(screen.getByRole('button', { name: /選択肢を開く/ }));
    expect(screen.getByRole('menu')).toBeInTheDocument();

    // メニュー外をクリック
    await user.click(screen.getByTestId('outside'));
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  });

  it('disabled時はクリック無効', async () => {
    const onClick1 = vi.fn();
    const actions = createActions({ onClick1 });
    const user = userEvent.setup();
    render(<SplitActionButton actions={actions} disabled />);

    const mainButton = screen.getByRole('button', { name: /送信/ });
    expect(mainButton).toBeDisabled();

    await user.click(mainButton);
    expect(onClick1).not.toHaveBeenCalled();

    const toggle = screen.getByRole('button', { name: /選択肢を開く/ });
    expect(toggle).toBeDisabled();
  });

  it('loading時はスピナー表示', () => {
    const actions = createActions();
    render(<SplitActionButton actions={actions} loading />);

    const mainButton = screen.getByRole('button', { name: /送信/ });
    expect(mainButton).toBeDisabled();
    expect(mainButton.querySelector('.processing-spinner')).toBeInTheDocument();
  });

  it('選択中のアイテムにチェックマークが表示される', async () => {
    const actions = createActions();
    const user = userEvent.setup();
    render(<SplitActionButton actions={actions} />);

    await user.click(screen.getByRole('button', { name: /選択肢を開く/ }));

    // デフォルトで送信が選択されている
    const sendItem = screen.getByRole('menuitem', { name: /送信/ });
    expect(sendItem.classList.contains('split-action-button-menu-item--selected')).toBe(true);
  });

  it('下書き選択後にメインボタンクリックで下書きのonClickが呼ばれる', async () => {
    const onClick2 = vi.fn();
    const actions = createActions({ onClick2 });
    const user = userEvent.setup();
    render(<SplitActionButton actions={actions} />);

    // メニューから下書きを選択
    await user.click(screen.getByRole('button', { name: /選択肢を開く/ }));
    await user.click(screen.getByRole('menuitem', { name: /下書き/ }));

    // メインボタンクリック
    await user.click(screen.getByRole('button', { name: /下書き/ }));

    expect(onClick2).toHaveBeenCalledTimes(1);
  });
});
