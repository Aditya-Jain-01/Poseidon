import React, { useState } from 'react';
import Card from '../../components/common/Card';
import TabBar from '../../components/common/TabBar';
import EmptyState from '../../components/common/EmptyState';
import { Radio } from 'lucide-react';
import './Gateway.css';

export function Gateway() {
  const [activeTab, setActiveTab] = useState('all');

  const tabs = [
    { key: 'all', label: 'All Channels', count: 0 },
    { key: 'web', label: 'Web/CLI', count: 0 },
    { key: 'telegram', label: 'Telegram', count: 0 },
    { key: 'discord', label: 'Discord', count: 0 },
  ];

  return (
    <div className="gateway-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Gateway</h1>
          <p className="page-subtitle">Cross-channel message routing and gateway status</p>
        </div>
      </div>

      <Card>
        <TabBar tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />
        <div style={{ marginTop: '20px' }}>
          <EmptyState
            icon={Radio}
            title="No Gateway Events"
            subtitle="Cross-channel message feed will appear here as external webhooks trigger agent runs."
          />
        </div>
      </Card>
    </div>
  );
}

export default Gateway;
