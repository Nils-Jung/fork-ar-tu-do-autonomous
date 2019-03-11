#include "wall.h"

Wall::Wall(float angle1, float angle2, float range1, float range2)
    : m_angle1{ angle1 }
    , m_angle2{ angle2 }
    , m_range1{ range1 }
    , m_range2{ range2 }
{
}

float Wall::getAngle()
{
    return atan((m_range1 * cos(std::abs(m_angle1 - m_angle2)) - m_range2) / m_range1 *
                sin(std::abs(m_angle1 - m_angle2)));
}

float Wall::predictDistance(float distancce_to_current_position)
{
    float angle = this->getAngle();
    float currentWallDistance = m_range2 * cos(angle);
    return currentWallDistance + distancce_to_current_position * sin(angle);
}

void Wall::draw(RvizGeometryPublisher& geometry, int id, std_msgs::ColorRGBA color)
{
    geometry.drawLine(id, createPoint(m_range1 * cos(m_angle1), m_range1 * sin(m_angle1), 0.0),
                      createPoint(m_range2 * cos(m_angle2), m_range2 * sin(m_angle2), 0.0), color, 0.03);
}