/**
 * Contacts management page.
 * Requirements: 1.5, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 5.1, 5.2, 5.3
 * Character Selection: 5.1, 5.2, 5.3, 5.4
 */

import { useCallback, useState } from 'react';
import { IoArrowBackOutline } from 'react-icons/io5';
import { Link } from 'react-router-dom';
import { CharacterSelector } from '../components/CharacterSelector';
import { ContactForm } from '../components/ContactForm';
import { ContactList } from '../components/ContactList';

/**
 * Contacts management page component.
 *
 * Features:
 * - Character selection
 * - Contact registration form
 * - Contact list with learning status
 * - Delete functionality
 * - Polling for learning status updates
 */
export function ContactsPage() {
  const [refreshKey, setRefreshKey] = useState(0);

  const handleContactCreated = useCallback(() => {
    // Trigger ContactList refresh
    setRefreshKey((prev) => prev + 1);
  }, []);

  return (
    <div className="contacts-page">
      <div className="contacts-header">
        <h2>連絡先管理</h2>
        <Link to="/emails" className="nav-back-button" aria-label="ダッシュボードへ戻る">
          <IoArrowBackOutline size={18} />
          <span>戻る</span>
        </Link>
      </div>

      <section>
        <ContactForm onSuccess={handleContactCreated} />
      </section>

      <section>
        <h3 className="contacts-section-title">登録済み連絡先</h3>
        <ContactList key={refreshKey} />
      </section>

      <section>
        <h2 className="contacts-section-heading">キャラクター選択</h2>
        <CharacterSelector />
      </section>
    </div>
  );
}
