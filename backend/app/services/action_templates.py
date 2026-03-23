"""
TBAPS Intervention Action Templates

Predefined action templates for different intervention categories.
These templates provide structured, actionable guidance for managers and HR.
"""

from typing import Dict, List, Any


class ActionTemplates:
    """
    Action templates for intervention recommendations
    
    Provides structured, actionable steps for:
    - Wellness interventions
    - Performance interventions
    - Engagement interventions
    - Development interventions
    - Team interventions
    """
    
    # ========================================================================
    # WELLNESS INTERVENTIONS
    # ========================================================================
    
    WELLNESS_CRITICAL = {
        'title': 'Critical Burnout Risk - Immediate Intervention',
        'timeline': '3 days',
        'actions': [
            {
                'step': 1,
                'action': 'Immediate Manager 1:1',
                'description': 'Schedule urgent 1:1 within 24 hours to discuss wellbeing',
                'owner': 'Manager',
                'duration': '30-60 minutes',
                'talking_points': [
                    'Express concern for employee wellbeing',
                    'Listen actively to concerns',
                    'Avoid judgment or blame',
                    'Focus on support and solutions',
                ],
            },
            {
                'step': 2,
                'action': 'Immediate Time Off',
                'description': 'Offer 3-5 days immediate time off',
                'owner': 'Manager + HR',
                'duration': '3-5 days',
                'notes': 'No questions asked, fully paid, encourage complete disconnect',
            },
            {
                'step': 3,
                'action': 'Workload Reduction',
                'description': 'Reduce workload by 50% for next 2 weeks',
                'owner': 'Manager',
                'duration': '2 weeks',
                'implementation': [
                    'Reassign non-critical tasks',
                    'Postpone deadlines',
                    'Redistribute to team',
                    'Document changes',
                ],
            },
            {
                'step': 4,
                'action': 'EAP Connection',
                'description': 'Connect with Employee Assistance Program',
                'owner': 'HR',
                'duration': 'Ongoing',
                'resources': [
                    'EAP hotline number',
                    'Counseling services',
                    'Mental health resources',
                    'Wellness programs',
                ],
            },
            {
                'step': 5,
                'action': 'Weekly Check-ins',
                'description': 'Schedule weekly wellbeing check-ins for next month',
                'owner': 'Manager',
                'duration': '4 weeks',
                'frequency': 'Weekly',
            },
        ],
        'success_metrics': [
            'Employee reports feeling better',
            'Workload is manageable',
            'Taking time off regularly',
            'Engaging with support resources',
        ],
    }
    
    WELLNESS_HIGH = {
        'title': 'High Burnout Risk - Wellness Support',
        'timeline': '7 days',
        'actions': [
            {
                'step': 1,
                'action': 'Wellness Check-in',
                'description': 'Schedule 1:1 within 7 days to discuss wellbeing',
                'owner': 'Manager',
                'duration': '30-45 minutes',
            },
            {
                'step': 2,
                'action': 'Wellness Program Enrollment',
                'description': 'Suggest and facilitate enrollment in wellness programs',
                'owner': 'HR',
                'programs': [
                    'Yoga or meditation classes',
                    'Fitness membership',
                    'Mental health counseling',
                    'Stress management workshops',
                ],
            },
            {
                'step': 3,
                'action': 'Workload Review',
                'description': 'Review and reduce workload by 25%',
                'owner': 'Manager',
                'duration': '2-4 weeks',
            },
            {
                'step': 4,
                'action': 'Encourage Vacation',
                'description': 'Encourage use of vacation time',
                'owner': 'Manager',
                'target': 'At least 5 days in next 2 months',
            },
            {
                'step': 5,
                'action': 'Bi-weekly Check-ins',
                'description': 'Schedule bi-weekly wellbeing check-ins',
                'owner': 'Manager',
                'duration': '2 months',
            },
        ],
        'success_metrics': [
            'Improved work-life balance',
            'Reduced stress levels',
            'Regular time off',
            'Engagement with wellness programs',
        ],
    }
    
    WELLNESS_MEDIUM = {
        'title': 'Moderate Burnout Risk - Preventive Action',
        'timeline': '14 days',
        'actions': [
            {
                'step': 1,
                'action': 'Wellness Check-in',
                'description': 'Schedule wellness discussion',
                'owner': 'Manager',
                'duration': '30 minutes',
            },
            {
                'step': 2,
                'action': 'Share Wellness Resources',
                'description': 'Provide information on available wellness programs',
                'owner': 'HR',
            },
            {
                'step': 3,
                'action': 'Work-Life Balance Review',
                'description': 'Discuss and improve work-life balance',
                'owner': 'Manager',
            },
            {
                'step': 4,
                'action': 'Encourage Regular Breaks',
                'description': 'Promote healthy work habits',
                'owner': 'Manager',
            },
        ],
        'success_metrics': [
            'Maintained work-life balance',
            'Awareness of wellness resources',
            'Regular breaks and time off',
        ],
    }
    
    # ========================================================================
    # PERFORMANCE INTERVENTIONS
    # ========================================================================
    
    PERFORMANCE_SUPPORT = {
        'title': 'Performance Support & Development',
        'timeline': '14 days',
        'actions': [
            {
                'step': 1,
                'action': 'Skills Assessment',
                'description': 'Conduct comprehensive skills gap analysis',
                'owner': 'Manager',
                'duration': '1-2 hours',
                'deliverable': 'Skills assessment report',
            },
            {
                'step': 2,
                'action': 'Targeted Training',
                'description': 'Enroll in training for identified skill gaps',
                'owner': 'Manager + L&D',
                'options': [
                    'Online courses (Udemy, Coursera, LinkedIn Learning)',
                    'Internal training programs',
                    'Workshops and seminars',
                    'Certification programs',
                ],
            },
            {
                'step': 3,
                'action': 'Mentor Assignment',
                'description': 'Assign experienced mentor or buddy',
                'owner': 'Manager',
                'duration': '3-6 months',
                'expectations': [
                    'Weekly 1:1 meetings',
                    'Code reviews or work reviews',
                    'Guidance and support',
                    'Career advice',
                ],
            },
            {
                'step': 4,
                'action': 'Project Rotation',
                'description': 'Assign to different project for skill development',
                'owner': 'Manager',
                'duration': '1-3 months',
            },
            {
                'step': 5,
                'action': 'Weekly 1:1s with Goals',
                'description': 'Regular check-ins with clear, measurable goals',
                'owner': 'Manager',
                'frequency': 'Weekly',
                'duration': '30 minutes',
            },
        ],
        'success_metrics': [
            'Skill improvement demonstrated',
            'Performance metrics improving',
            'Positive feedback from mentor',
            'Goals being met',
        ],
    }
    
    # ========================================================================
    # ENGAGEMENT INTERVENTIONS
    # ========================================================================
    
    ENGAGEMENT_RETENTION = {
        'title': 'Engagement & Retention Initiative',
        'timeline': '7 days',
        'actions': [
            {
                'step': 1,
                'action': 'Career Development Planning',
                'description': 'Comprehensive career planning session',
                'owner': 'Manager + HR',
                'duration': '60-90 minutes',
                'topics': [
                    'Career goals and aspirations',
                    'Skills to develop',
                    'Promotion timeline',
                    'Growth opportunities',
                ],
            },
            {
                'step': 2,
                'action': 'Growth Opportunities',
                'description': 'Identify and offer growth opportunities',
                'owner': 'Manager',
                'options': [
                    'New project leadership',
                    'Cross-functional collaboration',
                    'Skill expansion projects',
                    'Innovation initiatives',
                ],
            },
            {
                'step': 3,
                'action': 'Project Leadership Role',
                'description': 'Offer leadership opportunity on project',
                'owner': 'Manager',
                'duration': '2-6 months',
            },
            {
                'step': 4,
                'action': 'Recognition & Appreciation',
                'description': 'Formal recognition of contributions',
                'owner': 'Manager',
                'methods': [
                    'Public recognition in team meeting',
                    'Written appreciation email',
                    'Spot bonus or award',
                    'Peer recognition program',
                ],
            },
            {
                'step': 5,
                'action': 'Stay Interview',
                'description': 'Conduct stay interview to understand concerns',
                'owner': 'Manager or HR',
                'duration': '45-60 minutes',
                'questions': [
                    'What keeps you here?',
                    'What might make you leave?',
                    'What would make your job better?',
                    'How can we support your growth?',
                ],
            },
        ],
        'success_metrics': [
            'Improved engagement scores',
            'Clear career path defined',
            'Taking on leadership roles',
            'Positive sentiment in check-ins',
        ],
    }
    
    # ========================================================================
    # DEVELOPMENT INTERVENTIONS
    # ========================================================================
    
    DEVELOPMENT_LEADERSHIP = {
        'title': 'Leadership & Growth Opportunities',
        'timeline': '30 days',
        'actions': [
            {
                'step': 1,
                'action': 'Leadership Training Program',
                'description': 'Enroll in leadership development program',
                'owner': 'Manager + L&D',
                'duration': '3-6 months',
                'programs': [
                    'Internal leadership academy',
                    'External leadership courses',
                    'Executive coaching',
                    'Leadership workshops',
                ],
            },
            {
                'step': 2,
                'action': 'Mentorship Role',
                'description': 'Assign as mentor for junior team members',
                'owner': 'Manager',
                'duration': '6-12 months',
                'responsibilities': [
                    'Guide 1-2 junior employees',
                    'Regular mentoring sessions',
                    'Career guidance',
                    'Skill development support',
                ],
            },
            {
                'step': 3,
                'action': 'Strategic Project Assignment',
                'description': 'Lead high-visibility strategic project',
                'owner': 'Manager',
                'duration': '3-6 months',
            },
            {
                'step': 4,
                'action': 'Conference or Workshop',
                'description': 'Attend industry conference or workshop',
                'owner': 'Manager',
                'budget': 'Approved travel and registration',
            },
            {
                'step': 5,
                'action': 'Promotion Discussion',
                'description': 'Formal discussion about promotion timeline',
                'owner': 'Manager + HR',
                'duration': '60 minutes',
            },
        ],
        'success_metrics': [
            'Leadership skills demonstrated',
            'Successful mentoring relationships',
            'Strategic project delivered',
            'Promotion readiness',
        ],
    }
    
    # ========================================================================
    # TEAM INTERVENTIONS
    # ========================================================================
    
    TEAM_WELLNESS = {
        'title': 'Team Wellness Initiative',
        'timeline': '7 days',
        'actions': [
            {
                'step': 1,
                'action': 'Team Wellness Day',
                'description': 'Schedule dedicated team wellness day',
                'owner': 'Manager',
                'activities': [
                    'Team building activities',
                    'Wellness workshops',
                    'Relaxation activities',
                    'Team lunch or outing',
                ],
            },
            {
                'step': 2,
                'action': 'Workload Review',
                'description': 'Review and rebalance team workload',
                'owner': 'Manager',
                'deliverable': 'Workload distribution plan',
            },
            {
                'step': 3,
                'action': 'Flexible Work Arrangements',
                'description': 'Implement flexible work options',
                'owner': 'Manager + HR',
                'options': [
                    'Flexible hours',
                    'Remote work days',
                    'Compressed work weeks',
                    'No-meeting days',
                ],
            },
            {
                'step': 4,
                'action': 'Mental Health Resources',
                'description': 'Present mental health and wellness resources',
                'owner': 'HR',
                'duration': '30-45 minutes',
            },
        ],
        'success_metrics': [
            'Reduced team burnout levels',
            'Improved work-life balance',
            'Positive team sentiment',
            'Increased engagement',
        ],
    }
    
    TEAM_PERFORMANCE = {
        'title': 'Team Performance Enhancement',
        'timeline': '14 days',
        'actions': [
            {
                'step': 1,
                'action': 'Team Skills Assessment',
                'description': 'Assess team skills and gaps',
                'owner': 'Manager',
                'deliverable': 'Team skills matrix',
            },
            {
                'step': 2,
                'action': 'Group Training Sessions',
                'description': 'Organize team training on identified gaps',
                'owner': 'Manager + L&D',
                'duration': '2-4 weeks',
            },
            {
                'step': 3,
                'action': 'Process Improvement Workshop',
                'description': 'Facilitate process improvement session',
                'owner': 'Manager',
                'duration': 'Half day',
            },
            {
                'step': 4,
                'action': 'Knowledge Sharing Sessions',
                'description': 'Regular knowledge sharing meetings',
                'owner': 'Team',
                'frequency': 'Weekly or bi-weekly',
            },
        ],
        'success_metrics': [
            'Improved team performance metrics',
            'Skills gaps addressed',
            'Better processes implemented',
            'Increased knowledge sharing',
        ],
    }
    
    @classmethod
    def get_template(cls, category: str, priority: str) -> Dict[str, Any]:
        """
        Get action template for intervention
        
        Args:
            category: Intervention category (wellness, performance, etc.)
            priority: Priority level (critical, high, medium, low)
        
        Returns:
            Action template dictionary
        """
        template_map = {
            ('wellness', 'critical'): cls.WELLNESS_CRITICAL,
            ('wellness', 'high'): cls.WELLNESS_HIGH,
            ('wellness', 'medium'): cls.WELLNESS_MEDIUM,
            ('performance', 'medium'): cls.PERFORMANCE_SUPPORT,
            ('performance', 'high'): cls.PERFORMANCE_SUPPORT,
            ('engagement', 'high'): cls.ENGAGEMENT_RETENTION,
            ('engagement', 'medium'): cls.ENGAGEMENT_RETENTION,
            ('development', 'low'): cls.DEVELOPMENT_LEADERSHIP,
            ('team', 'high'): cls.TEAM_WELLNESS,
            ('team', 'medium'): cls.TEAM_PERFORMANCE,
        }
        
        return template_map.get((category, priority), {})
    
    @classmethod
    def get_all_templates(cls) -> Dict[str, Dict[str, Any]]:
        """Get all available templates"""
        return {
            'wellness_critical': cls.WELLNESS_CRITICAL,
            'wellness_high': cls.WELLNESS_HIGH,
            'wellness_medium': cls.WELLNESS_MEDIUM,
            'performance_support': cls.PERFORMANCE_SUPPORT,
            'engagement_retention': cls.ENGAGEMENT_RETENTION,
            'development_leadership': cls.DEVELOPMENT_LEADERSHIP,
            'team_wellness': cls.TEAM_WELLNESS,
            'team_performance': cls.TEAM_PERFORMANCE,
        }
