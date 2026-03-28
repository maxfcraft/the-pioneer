import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Card } from '../ui/Card';
import { PinkButton } from '../ui/PinkButton';
import { colors, spacing, typography, borderRadius } from '../../theme';
import type { Quest } from '../../types';

interface Props {
  quest: Quest;
  onComplete: (questId: string) => void;
}

const difficultyColors = {
  easy: colors.sage,
  medium: colors.lavender,
  adventurous: colors.goldLight,
};

export function QuestCard({ quest, onComplete }: Props) {
  const isCompleted = quest.status === 'completed';

  return (
    <Card style={isCompleted ? { ...styles.card, ...styles.completedCard } : styles.card}>
      <View style={styles.header}>
        <View style={[styles.badge, { backgroundColor: difficultyColors[quest.difficulty] }]}>
          <Text style={styles.badgeText}>{quest.difficulty}</Text>
        </View>
        <Text style={styles.reward}>+{quest.coinReward} coins</Text>
      </View>

      <Text style={styles.title}>{quest.title}</Text>
      <Text style={styles.description}>{quest.description}</Text>

      {!isCompleted ? (
        <PinkButton
          title="Mark Complete"
          onPress={() => onComplete(quest.id)}
          variant="primary"
          style={styles.button}
        />
      ) : (
        <View style={styles.completedBadge}>
          <Text style={styles.completedText}>Completed!</Text>
        </View>
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    marginBottom: spacing.md,
  },
  completedCard: {
    opacity: 0.8,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  badge: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: borderRadius.round,
  },
  badgeText: {
    fontSize: typography.sizes.xs,
    color: colors.text,
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  reward: {
    fontSize: typography.sizes.sm,
    color: colors.gold,
    fontWeight: '700',
  },
  title: {
    fontSize: typography.sizes.lg,
    fontWeight: '700',
    color: colors.text,
    marginBottom: spacing.xs,
  },
  description: {
    fontSize: typography.sizes.md,
    color: colors.textLight,
    lineHeight: 24,
    marginBottom: spacing.lg,
  },
  button: {
    alignSelf: 'stretch',
  },
  completedBadge: {
    backgroundColor: colors.sage,
    paddingVertical: spacing.sm,
    borderRadius: borderRadius.xl,
    alignItems: 'center',
  },
  completedText: {
    color: colors.text,
    fontWeight: '600',
    fontSize: typography.sizes.md,
  },
});
