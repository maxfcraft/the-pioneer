import { format, startOfDay, endOfDay, startOfWeek, endOfWeek } from 'date-fns';

export function getTodayString(): string {
  return format(new Date(), 'yyyy-MM-dd');
}

export function getTodayStart(): Date {
  return startOfDay(new Date());
}

export function getTodayEnd(): Date {
  return endOfDay(new Date());
}

export function getWeekStart(): Date {
  return startOfWeek(new Date(), { weekStartsOn: 1 }); // Monday
}

export function getWeekEnd(): Date {
  return endOfWeek(new Date(), { weekStartsOn: 1 });
}

export function formatDate(date: Date): string {
  return format(date, 'MMM d, yyyy');
}
