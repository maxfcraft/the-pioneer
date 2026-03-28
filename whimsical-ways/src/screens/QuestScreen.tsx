import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Alert } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { QuestCard } from '../components/quests/QuestCard';
import { colors, spacing, typography } from '../theme';
import type { Quest } from '../types';

// Hardcoded quests for Phase 1
const initialQuests: Quest[] = [
  {
    id: '1',
    title: 'Find a blue flower',
    description: 'Keep your eyes open on your walk today and photograph the first blue flower you spot. Nature is full of surprises!',
    difficulty: 'easy',
    coinReward: 100,
    status: 'active',
    assignedDate: '2026-03-28',
    completedAt: null,
    createdAt: new Date(),
  },
  {
    id: '2',
    title: 'Walk a new route',
    description: 'Take a turn you have never taken before. Explore a new street, trail, or path in your neighborhood.',
    difficulty: 'medium',
    coinReward: 200,
    status: 'active',
    assignedDate: '2026-03-28',
    completedAt: null,
    createdAt: new Date(),
  },
  {
    id: '3',
    title: 'Photograph the most interesting door',
    description: 'Find the most unique, colorful, or interesting door on your walk and snap a photo. Bonus points for character!',
    difficulty: 'adventurous',
    coinReward: 300,
    status: 'active',
    assignedDate: '2026-03-28',
    completedAt: null,
    createdAt: new Date(),
  },
];

export function QuestScreen() {
  const [quests, setQuests] = useState<Quest[]>(initialQuests);

  function handleComplete(questId: string) {
    Alert.alert(
      'Quest Complete!',
      'Nice work adventurer! Your bonus coins have been added.',
      [
        {
          text: 'Celebrate!',
          onPress: () => {
            setQuests((prev) =>
              prev.map((q) =>
                q.id === questId
                  ? { ...q, status: 'completed' as const, completedAt: new Date() }
                  : q
              )
            );
          },
        },
      ]
    );
  }

  const activeQuests = quests.filter((q) => q.status === 'active');
  const completedQuests = quests.filter((q) => q.status === 'completed');

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
        <Text style={styles.title}>Today's Quests</Text>
        <Text style={styles.subtitle}>Complete quests on your walk to earn bonus coins</Text>

        {activeQuests.length > 0 && (
          <View style={styles.section}>
            {activeQuests.map((quest) => (
              <QuestCard key={quest.id} quest={quest} onComplete={handleComplete} />
            ))}
          </View>
        )}

        {completedQuests.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Completed</Text>
            {completedQuests.map((quest) => (
              <QuestCard key={quest.id} quest={quest} onComplete={handleComplete} />
            ))}
          </View>
        )}

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
  title: {
    fontSize: typography.sizes.xl,
    fontWeight: '700',
    color: colors.text,
    marginBottom: spacing.xs,
  },
  subtitle: {
    fontSize: typography.sizes.sm,
    color: colors.textLight,
    marginBottom: spacing.xl,
  },
  section: {
    marginBottom: spacing.lg,
  },
  sectionTitle: {
    fontSize: typography.sizes.md,
    fontWeight: '600',
    color: colors.textMuted,
    marginBottom: spacing.md,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  bottomPadding: {
    height: spacing.xxl,
  },
});
