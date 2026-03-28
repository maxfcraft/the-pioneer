import React from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { StepRing } from '../components/home/StepRing';
import { CoinBadge } from '../components/ui/CoinBadge';
import { DailyQuestCard } from '../components/home/DailyQuestCard';
import { useSteps } from '../hooks/useSteps';
import { useCoins } from '../hooks/useCoins';
import { colors, spacing, typography } from '../theme';
import type { Quest } from '../types';

// Mock data for now
const DAILY_GOAL = 10000;
const mockQuest: Quest = {
  id: '1',
  title: 'Find a blue flower',
  description: 'Keep your eyes open on your walk today and photograph the first blue flower you spot. Nature is full of surprises!',
  difficulty: 'easy',
  coinReward: 100,
  status: 'active',
  assignedDate: '2026-03-28',
  completedAt: null,
  createdAt: new Date(),
};

export function HomeScreen({ navigation }: any) {
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
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.greeting}>Good morning</Text>
          <CoinBadge coins={coins} size="md" />
        </View>

        {/* Step Ring */}
        <View style={styles.ringContainer}>
          <StepRing steps={steps} goal={DAILY_GOAL} size={220} />
        </View>

        {/* Locked photos count */}
        <View style={styles.photoHint}>
          <Text style={styles.photoHintText}>
            {steps >= DAILY_GOAL
              ? 'Your photos are developed!'
              : `${Math.max(DAILY_GOAL - steps, 0).toLocaleString()} steps to reveal your photos`}
          </Text>
        </View>

        {/* Today's Quest */}
        <DailyQuestCard
          quest={mockQuest}
          onPress={() => navigation.navigate('Quests')}
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
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    marginBottom: spacing.xl,
  },
  greeting: {
    fontSize: typography.sizes.xl,
    fontWeight: '700',
    color: colors.text,
  },
  ringContainer: {
    alignItems: 'center',
    marginBottom: spacing.lg,
  },
  photoHint: {
    alignItems: 'center',
    marginBottom: spacing.xl,
  },
  photoHintText: {
    fontSize: typography.sizes.sm,
    color: colors.textLight,
    fontStyle: 'italic',
  },
  bottomPadding: {
    height: spacing.xxl,
  },
});
