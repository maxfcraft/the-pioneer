import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { LeaderboardEntry } from '../components/social/LeaderboardEntry';
import { colors, spacing, typography, borderRadius } from '../theme';

type TabType = 'steps' | 'coins';

// Mock leaderboard data
const mockLeaderboard = [
  { userId: '1', displayName: 'Emma', avatarUrl: null, weeklySteps: 72400, weeklyCoins: 72400 },
  { userId: '2', displayName: 'Sophia', avatarUrl: null, weeklySteps: 68200, weeklyCoins: 68200 },
  { userId: 'me', displayName: 'You', avatarUrl: null, weeklySteps: 54100, weeklyCoins: 54100 },
  { userId: '3', displayName: 'Olivia', avatarUrl: null, weeklySteps: 49800, weeklyCoins: 49800 },
  { userId: '4', displayName: 'Ava', avatarUrl: null, weeklySteps: 41200, weeklyCoins: 41200 },
  { userId: '5', displayName: 'Mia', avatarUrl: null, weeklySteps: 38500, weeklyCoins: 38500 },
];

export function LeaderboardScreen() {
  const [activeTab, setActiveTab] = useState<TabType>('steps');

  return (
    <LinearGradient
      colors={[colors.cream, colors.pinkLight, colors.cream]}
      style={styles.gradient}
    >
      <View style={styles.container}>
        <Text style={styles.title}>Leaderboard</Text>
        <Text style={styles.subtitle}>This week</Text>

        {/* Tab Switcher */}
        <View style={styles.tabs}>
          <TouchableOpacity
            style={[styles.tab, activeTab === 'steps' && styles.activeTab]}
            onPress={() => setActiveTab('steps')}
          >
            <Text style={[styles.tabText, activeTab === 'steps' && styles.activeTabText]}>
              Steps
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.tab, activeTab === 'coins' && styles.activeTab]}
            onPress={() => setActiveTab('coins')}
          >
            <Text style={[styles.tabText, activeTab === 'coins' && styles.activeTabText]}>
              Coins
            </Text>
          </TouchableOpacity>
        </View>

        {/* Leaderboard List */}
        <ScrollView showsVerticalScrollIndicator={false}>
          {mockLeaderboard
            .sort((a, b) =>
              activeTab === 'steps'
                ? b.weeklySteps - a.weeklySteps
                : b.weeklyCoins - a.weeklyCoins
            )
            .map((entry, index) => (
              <LeaderboardEntry
                key={entry.userId}
                rank={index + 1}
                displayName={entry.displayName}
                avatarUrl={entry.avatarUrl}
                value={activeTab === 'steps' ? entry.weeklySteps : entry.weeklyCoins}
                type={activeTab}
                isCurrentUser={entry.userId === 'me'}
              />
            ))}

          {mockLeaderboard.length === 0 && (
            <View style={styles.empty}>
              <Text style={styles.emptyText}>Add friends to see the leaderboard!</Text>
            </View>
          )}
        </ScrollView>
      </View>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  gradient: {
    flex: 1,
  },
  container: {
    flex: 1,
    paddingTop: spacing.xxl + spacing.xl,
    paddingHorizontal: spacing.md,
  },
  title: {
    fontSize: typography.sizes.xl,
    fontWeight: '700',
    color: colors.text,
    marginBottom: spacing.xs,
  },
  subtitle: {
    fontSize: typography.sizes.sm,
    color: colors.textLight,
    marginBottom: spacing.lg,
  },
  tabs: {
    flexDirection: 'row',
    backgroundColor: colors.white,
    borderRadius: borderRadius.xl,
    padding: spacing.xs,
    marginBottom: spacing.lg,
  },
  tab: {
    flex: 1,
    paddingVertical: spacing.sm,
    alignItems: 'center',
    borderRadius: borderRadius.lg,
  },
  activeTab: {
    backgroundColor: colors.pinkAccent,
  },
  tabText: {
    fontSize: typography.sizes.md,
    fontWeight: '600',
    color: colors.textLight,
  },
  activeTabText: {
    color: colors.white,
  },
  empty: {
    alignItems: 'center',
    paddingTop: spacing.xxl * 2,
  },
  emptyText: {
    fontSize: typography.sizes.md,
    color: colors.textMuted,
  },
});
