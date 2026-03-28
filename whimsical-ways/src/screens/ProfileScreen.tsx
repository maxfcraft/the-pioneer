import React from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Card } from '../components/ui/Card';
import { CoinBadge } from '../components/ui/CoinBadge';
import { PinkButton } from '../components/ui/PinkButton';
import { useSteps } from '../hooks/useSteps';
import { useCoins } from '../hooks/useCoins';
import { colors, spacing, typography, borderRadius } from '../theme';
import { formatSteps } from '../utils/coins';

export function ProfileScreen() {
  const { steps } = useSteps();
  const coins = useCoins(steps);

  return (
    <LinearGradient
      colors={[colors.cream, colors.pinkLight, colors.cream]}
      style={styles.gradient}
    >
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        {/* Profile Header */}
        <View style={styles.profileHeader}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>W</Text>
          </View>
          <Text style={styles.name}>Whimsical Walker</Text>
          <CoinBadge coins={coins} size="lg" />
        </View>

        {/* Stats Grid */}
        <View style={styles.statsGrid}>
          <Card style={styles.statCard}>
            <Text style={styles.statValue}>{formatSteps(steps)}</Text>
            <Text style={styles.statLabel}>Steps Today</Text>
          </Card>
          <Card style={styles.statCard}>
            <Text style={styles.statValue}>3</Text>
            <Text style={styles.statLabel}>Quests Done</Text>
          </Card>
          <Card style={styles.statCard}>
            <Text style={styles.statValue}>5</Text>
            <Text style={styles.statLabel}>Day Streak</Text>
          </Card>
          <Card style={styles.statCard}>
            <Text style={styles.statValue}>12</Text>
            <Text style={styles.statLabel}>Photos</Text>
          </Card>
        </View>

        {/* Settings */}
        <Card style={styles.settingsCard}>
          <Text style={styles.settingsTitle}>Settings</Text>

          <View style={styles.settingRow}>
            <Text style={styles.settingLabel}>Daily Step Goal</Text>
            <Text style={styles.settingValue}>10,000</Text>
          </View>

          <View style={styles.settingRow}>
            <Text style={styles.settingLabel}>Notifications</Text>
            <Text style={styles.settingValue}>On</Text>
          </View>

          <View style={styles.settingRow}>
            <Text style={styles.settingLabel}>Health Data</Text>
            <Text style={styles.settingValue}>Connected</Text>
          </View>
        </Card>

        {/* Adventure Journal Link */}
        <PinkButton
          title="View Adventure Journal"
          onPress={() => {}}
          variant="secondary"
          style={styles.journalButton}
        />

        <View style={styles.bottomPadding} />
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  gradient: {
    flex: 1,
  },
  container: {
    flex: 1,
  },
  content: {
    paddingTop: spacing.xxl + spacing.xl,
    paddingHorizontal: spacing.md,
  },
  profileHeader: {
    alignItems: 'center',
    marginBottom: spacing.xl,
  },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: colors.pinkAccent,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.md,
  },
  avatarText: {
    color: colors.white,
    fontSize: typography.sizes.xxl,
    fontWeight: '700',
  },
  name: {
    fontSize: typography.sizes.xl,
    fontWeight: '700',
    color: colors.text,
    marginBottom: spacing.md,
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginBottom: spacing.lg,
  },
  statCard: {
    width: '48%',
    alignItems: 'center',
    marginBottom: spacing.md,
    padding: spacing.md,
  },
  statValue: {
    fontSize: typography.sizes.xl,
    fontWeight: '700',
    color: colors.pinkAccent,
  },
  statLabel: {
    fontSize: typography.sizes.xs,
    color: colors.textLight,
    marginTop: spacing.xs,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  settingsCard: {
    marginBottom: spacing.lg,
  },
  settingsTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: '700',
    color: colors.text,
    marginBottom: spacing.md,
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.pinkLight,
  },
  settingLabel: {
    fontSize: typography.sizes.md,
    color: colors.text,
  },
  settingValue: {
    fontSize: typography.sizes.md,
    color: colors.textLight,
    fontWeight: '500',
  },
  journalButton: {
    marginBottom: spacing.lg,
  },
  bottomPadding: {
    height: spacing.xxl,
  },
});
