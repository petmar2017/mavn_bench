import React from 'react';
import classNames from 'classnames';
import styles from './ViewerTabBar.module.css';

export type ViewerTab = {
  id: string;
  label: string;
  icon?: React.ReactNode;
}

interface ViewerTabBarProps {
  tabs: ViewerTab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
  className?: string;
}

export const ViewerTabBar: React.FC<ViewerTabBarProps> = ({
  tabs,
  activeTab,
  onTabChange,
  className
}) => {
  return (
    <div className={classNames(styles.tabBar, className)}>
      <div className={styles.tabs}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={classNames(styles.tab, {
              [styles.active]: activeTab === tab.id,
            })}
            onClick={() => onTabChange(tab.id)}
          >
            {tab.icon && <span className={styles.tabIcon}>{tab.icon}</span>}
            <span className={styles.tabLabel}>{tab.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
};