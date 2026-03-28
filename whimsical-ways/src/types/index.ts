export interface User {
  uid: string;
  displayName: string;
  avatarUrl: string | null;
  email: string;
  dailyStepGoal: number;
  totalCoins: number;
  totalSteps: number;
  currentStreak: number;
  longestStreak: number;
  friendIds: string[];
  createdAt: Date;
}

export interface DailySteps {
  date: string; // "YYYY-MM-DD"
  steps: number;
  goalMet: boolean;
  coinsEarned: number;
  syncedAt: Date;
}

export interface Quest {
  id: string;
  title: string;
  description: string;
  difficulty: 'easy' | 'medium' | 'adventurous';
  coinReward: number;
  status: 'active' | 'completed' | 'expired';
  assignedDate: string;
  completedAt: Date | null;
  createdAt: Date;
}

export interface Photo {
  id: string;
  localUri: string;
  cloudUrl: string | null;
  isRevealed: boolean;
  takenAt: Date;
  takenOnDate: string; // "YYYY-MM-DD"
  revealedAt: Date | null;
  questId: string | null;
}

export interface FriendRequest {
  id: string;
  fromUserId: string;
  toUserId: string;
  status: 'pending' | 'accepted' | 'declined';
  createdAt: Date;
}

export interface LeaderboardEntry {
  userId: string;
  displayName: string;
  avatarUrl: string | null;
  weeklySteps: number;
  weeklyCoins: number;
  weeklyQuestsCompleted: number;
}
