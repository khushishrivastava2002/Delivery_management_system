import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  ScrollView,
  RefreshControl,
  Switch,
  ActivityIndicator,
  Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../../contexts/AuthContext';
import { DeliveryPersonStatus } from '../../types';
import { Ionicons } from '@expo/vector-icons';
import api from '../../utils/api';

interface Stats {
  today: number;
  this_week: number;
  this_month: number;
}

export default function Profile() {
  const [stats, setStats] = useState<Stats>({ today: 0, this_week: 0, this_month: 0 });
  const [refreshing, setRefreshing] = useState(false);
  const [statusLoading, setStatusLoading] = useState(false);
  const [logoutLoading, setLogoutLoading] = useState(false);
  const { user, logout, updateStatus, refreshUser } = useAuth();
  const router = useRouter();

  const fetchStats = async () => {
    try {
      const response = await api.get('/stats/orders');
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await Promise.all([fetchStats(), refreshUser()]);
    } catch (error) {
      console.error('Error refreshing data:', error);
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchStats();
    refreshUser();
  }, []);

  const onRefresh = () => {
    handleRefresh();
  };

  const handleStatusToggle = async (value: boolean) => {
    const newStatus = value ? DeliveryPersonStatus.ACTIVE : DeliveryPersonStatus.INACTIVE;
    setStatusLoading(true);
    try {
      await updateStatus(newStatus);
    } catch (error) {
      Alert.alert('Error', 'Failed to update status');
    } finally {
      setStatusLoading(false);
    }
  };

  const performLogout = async () => {
    setLogoutLoading(true);
    try {
      await logout();
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      setLogoutLoading(false);
      router.replace('/login');
    }
  };

  const handleLogout = () => {
    if (Platform.OS === 'web') {
      if (window.confirm('Are you sure you want to logout?')) {
        performLogout();
      }
      return;
    }

    Alert.alert(
      'Logout',
      'Are you sure you want to logout?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Logout',
          style: 'destructive',
          onPress: performLogout,
        },
      ],
      { cancelable: true }
    );
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor="#6366F1"
        />
      }
    >
      <View style={styles.profileSection}>
        <View style={styles.avatarContainer}>
          <Ionicons name="person" size={56} color="#6366F1" />
        </View>
        <Text style={styles.name}>{user?.name}</Text>
        <View style={styles.contactInfo}>
          <View style={styles.infoRow}>
            <Ionicons name="mail" size={16} color="#6B7280" />
            <Text style={styles.email}>{user?.email}</Text>
          </View>
          <View style={styles.infoRow}>
            <Ionicons name="call" size={16} color="#6B7280" />
            <Text style={styles.phone}>{user?.phone}</Text>
          </View>
        </View>
      </View>

      <View style={styles.statusSection}>
        <View style={styles.statusHeader}>
          <Text style={styles.sectionTitle}>Availability Status</Text>
          <View style={[
            styles.statusBadge,
            { backgroundColor: user?.status === DeliveryPersonStatus.ACTIVE ? '#D1FAE5' : '#F3F4F6' }
          ]}>
            <Text style={[
              styles.statusText,
              { color: user?.status === DeliveryPersonStatus.ACTIVE ? '#059669' : '#6B7280' }
            ]}>
              {user?.status === DeliveryPersonStatus.ACTIVE ? 'On Duty' : 'Off Duty'}
            </Text>
          </View>
        </View>
        <View style={styles.statusToggle}>
          <Text style={styles.statusDescription}>
            {user?.status === DeliveryPersonStatus.ACTIVE
              ? 'You are currently receiving orders'
              : 'You are currently offline'}
          </Text>
          {statusLoading ? (
            <ActivityIndicator size="small" color="#6366F1" />
          ) : (
            <Switch
              trackColor={{ false: '#E5E7EB', true: '#818CF8' }}
              thumbColor={user?.status === DeliveryPersonStatus.ACTIVE ? '#4F46E5' : '#f4f3f4'}
              ios_backgroundColor="#E5E7EB"
              onValueChange={handleStatusToggle}
              value={user?.status === DeliveryPersonStatus.ACTIVE}
            />
          )}
        </View>
      </View>

      <View style={styles.statsSection}>
        <Text style={styles.sectionTitle}>Delivery Statistics</Text>
        <Text style={styles.sectionSubtitle}>Your performance overview</Text>

        <View style={styles.statsGrid}>
          <View style={[styles.statCard, { borderColor: '#F59E0B' }]}>
            <View style={[styles.statIconContainer, { backgroundColor: '#FEF3C7' }]}>
              <Ionicons name="today" size={28} color="#F59E0B" />
            </View>
            <Text style={styles.statValue}>{stats.today}</Text>
            <Text style={styles.statLabel}>Today</Text>
          </View>

          <View style={[styles.statCard, { borderColor: '#3B82F6' }]}>
            <View style={[styles.statIconContainer, { backgroundColor: '#DBEAFE' }]}>
              <Ionicons name="calendar" size={28} color="#3B82F6" />
            </View>
            <Text style={styles.statValue}>{stats.this_week}</Text>
            <Text style={styles.statLabel}>This Week</Text>
          </View>

          <View style={[styles.statCard, { borderColor: '#10B981' }]}>
            <View style={[styles.statIconContainer, { backgroundColor: '#D1FAE5' }]}>
              <Ionicons name="calendar-outline" size={28} color="#10B981" />
            </View>
            <Text style={styles.statValue}>{stats.this_month}</Text>
            <Text style={styles.statLabel}>This Month</Text>
          </View>
        </View>
      </View>

      <TouchableOpacity
        style={[styles.logoutButton, logoutLoading && styles.logoutButtonDisabled]}
        onPress={handleLogout}
        disabled={logoutLoading}
      >
        {logoutLoading ? (
          <ActivityIndicator size="small" color="#fff" />
        ) : (
          <>
            <Ionicons name="log-out-outline" size={22} color="#fff" />
            <Text style={styles.logoutText}>Logout</Text>
          </>
        )}
      </TouchableOpacity>

      <Text style={styles.versionText}>Version 1.0.0</Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F9FAFB',
  },
  content: {
    padding: 20,
    paddingBottom: 40,
  },
  profileSection: {
    backgroundColor: '#fff',
    borderRadius: 20,
    padding: 32,
    alignItems: 'center',
    marginBottom: 20,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  avatarContainer: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: '#EEF2FF',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
    borderWidth: 4,
    borderColor: '#fff',
    shadowColor: '#6366F1',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 12,
    elevation: 4,
  },
  name: {
    fontSize: 26,
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: 16,
  },
  contactInfo: {
    gap: 8,
    alignItems: 'center',
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  email: {
    fontSize: 14,
    color: '#6B7280',
  },
  phone: {
    fontSize: 14,
    color: '#6B7280',
  },
  statusSection: {
    backgroundColor: '#fff',
    borderRadius: 20,
    padding: 20,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  statusHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusText: {
    fontSize: 12,
    fontWeight: '600',
  },
  statusToggle: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  statusDescription: {
    fontSize: 14,
    color: '#6B7280',
  },
  statsSection: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: 4,
  },
  sectionSubtitle: {
    fontSize: 14,
    color: '#6B7280',
    marginBottom: 16,
  },
  statsGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 12,
  },
  statCard: {
    flex: 1,
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 20,
    alignItems: 'center',
    borderWidth: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  statIconContainer: {
    width: 56,
    height: 56,
    borderRadius: 28,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
  },
  statValue: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 12,
    color: '#6B7280',
    fontWeight: '500',
  },
  logoutButton: {
    backgroundColor: '#EF4444',
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 10,
    shadowColor: '#EF4444',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  logoutText: {
    color: '#fff',
    fontSize: 17,
    fontWeight: '600',
  },
  versionText: {
    textAlign: 'center',
    marginTop: 20,
    fontSize: 12,
    color: '#9CA3AF',
  },
  logoutButtonDisabled: {
    opacity: 0.7,
  },
});
