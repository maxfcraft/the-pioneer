import React from 'react';
import { View, Text, StyleSheet, FlatList } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { PolaroidCard } from '../components/polaroids/PolaroidCard';
import { useSteps } from '../hooks/useSteps';
import { colors, spacing, typography } from '../theme';
import type { Photo } from '../types';

// Mock photos for demonstration
const mockPhotos: Photo[] = [
  {
    id: '1',
    localUri: 'https://picsum.photos/400/400?random=1',
    cloudUrl: null,
    isRevealed: false,
    takenAt: new Date(),
    takenOnDate: '2026-03-28',
    revealedAt: null,
    questId: '1',
  },
  {
    id: '2',
    localUri: 'https://picsum.photos/400/400?random=2',
    cloudUrl: null,
    isRevealed: false,
    takenAt: new Date(),
    takenOnDate: '2026-03-28',
    revealedAt: null,
    questId: null,
  },
  {
    id: '3',
    localUri: 'https://picsum.photos/400/400?random=3',
    cloudUrl: null,
    isRevealed: true,
    takenAt: new Date(),
    takenOnDate: '2026-03-27',
    revealedAt: new Date(),
    questId: '2',
  },
];

export function PolaroidsScreen() {
  const { steps } = useSteps();
  const dailyGoal = 10000;
  const stepsRemaining = Math.max(dailyGoal - steps, 0);

  return (
    <LinearGradient
      colors={[colors.cream, colors.pinkLight, colors.cream]}
      style={styles.gradient}
    >
      <View style={styles.container}>
        <Text style={styles.title}>Your Polaroids</Text>
        <Text style={styles.subtitle}>
          {stepsRemaining > 0
            ? `${stepsRemaining.toLocaleString()} steps until today's photos develop`
            : "Today's photos are revealed!"}
        </Text>

        <FlatList
          data={mockPhotos}
          numColumns={2}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.grid}
          columnWrapperStyle={styles.row}
          showsVerticalScrollIndicator={false}
          renderItem={({ item, index }) => (
            <View style={[styles.gridItem, index % 2 === 1 && { transform: [{ rotate: '1deg' }] }]}>
              <PolaroidCard
                photo={item}
                stepsRemaining={item.isRevealed ? 0 : stepsRemaining}
              />
            </View>
          )}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Text style={styles.emptyText}>No photos yet</Text>
              <Text style={styles.emptySubtext}>Take photos during your walk!</Text>
            </View>
          }
        />
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
    fontStyle: 'italic',
    marginBottom: spacing.lg,
  },
  grid: {
    paddingBottom: spacing.xxl,
  },
  row: {
    justifyContent: 'space-between',
    marginBottom: spacing.md,
  },
  gridItem: {
    width: '48%',
  },
  empty: {
    alignItems: 'center',
    paddingTop: spacing.xxl * 2,
  },
  emptyText: {
    fontSize: typography.sizes.lg,
    fontWeight: '600',
    color: colors.textMuted,
  },
  emptySubtext: {
    fontSize: typography.sizes.sm,
    color: colors.textMuted,
    marginTop: spacing.xs,
  },
});
