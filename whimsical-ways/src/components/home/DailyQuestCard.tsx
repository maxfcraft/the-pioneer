import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Card } from '../ui/Card';
import { colors, spacing, typography, borderRadius } from '../../theme';
import type { Quest } from '../../types';

interface Props {
  quest: Quest | null;
  onPress: () => void;
}

const difficultyColors = {
  easy: colors.sage,
  medium: colors.lavender,
  adventurous: colors.goldLight,
};

export function DailyQuestCard({ quest, onPress }: Props) {
  if (!quest) {
    return (
      <Card style={styles.card}>
        <Text style={styles.emptyTitle}>No quest today</Text>
        <Text style={styles.emptyText}>Check back tomorrow for a new adventure!</Text>
      </Card>
    );
  }

  return (
    <TouchableOpacity onPress={onPress} activeOpacity={0.8}>
      <Card style={styles.card}>
        <View style={styles.header}>
          <Text style={styles.label}>Today's Quest</Text>
          <View style={[styles.badge, { backgroundColor: difficultyColors[quest.difficulty] }]}>
            <Text style={styles.badgeText}>{quest.difficulty}</Text>
          </View>
        </View>
        <Text style={styles.title}>{quest.title}</Text>
        <Text style={styles.description} numberOfLines={2}>{quest.description}</Text>
        <View style={styles.footer}>
          <Text style={styles.reward}>+{quest.coinReward} coins</Text>
          {quest.status === 'completed' && (
            <Text style={styles.completed}>Completed</Text>
          )}
        </View>
      </Card>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    marginHorizontal: spacing.md,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  label: {
    fontSize: typography.sizes.xs,
    color: colors.textMuted,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  badge: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: borderRadius.round,
  },
  badgeText: {
    fontSize: typography.sizes.xs,
    color: colors.text,
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  title: {
    fontSize: typography.sizes.lg,
    fontWeight: '700',
    color: colors.text,
    marginBottom: spacing.xs,
  },
  description: {
    fontSize: typography.sizes.sm,
    color: colors.textLight,
    lineHeight: 20,
    marginBottom: spacing.md,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  reward: {
    fontSize: typography.sizes.sm,
    color: colors.gold,
    fontWeight: '700',
  },
  completed: {
    fontSize: typography.sizes.sm,
    color: colors.sage,
    fontWeight: '600',
  },
  emptyTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: '600',
    color: colors.textMuted,
    textAlign: 'center',
  },
  emptyText: {
    fontSize: typography.sizes.sm,
    color: colors.textMuted,
    textAlign: 'center',
    marginTop: spacing.xs,
  },
});
