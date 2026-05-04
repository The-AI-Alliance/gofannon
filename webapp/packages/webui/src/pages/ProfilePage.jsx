import React from 'react';
import ApiKeysTab from '../components/profile/ApiKeysTab';

// ProfilePage previously had Basic Info / Usage / Billing tabs that were
// placeholders without real functionality. Now collapsed to just API Keys —
// the only section that does anything. The :section URL param is preserved
// so /profile/apikeys still works (and so do any cached bookmarks); other
// values fall through to the same view.
const ProfilePage = () => <ApiKeysTab />;

export default ProfilePage;
