resource "aws_elasticache_subnet_group" "main" {
  name        = "${var.project_name}-redis-subnet-group"
  description = "ElastiCache subnet group"
  subnet_ids  = aws_subnet.private[*].id
}

resource "aws_elasticache_replication_group" "main" {
  replication_group_id          = "${var.project_name}-${var.environment}"
  description                   = "Redis for MCP Bridge"
  node_type                     = var.redis_node_type
  num_cache_clusters            = 2
  port                          = 6379
  engine                        = "redis"
  engine_version                = "7"
  parameter_group_name          = "default.redis7"
  subnet_group_name             = aws_elasticache_subnet_group.main.name
  security_group_ids            = [aws_security_group.redis.id]

  automatic_failover_enabled    = true
  multi_az_enabled              = true
  at_rest_encryption_enabled    = true
  transit_encryption_enabled    = true

  auto_minor_version_upgrade    = true
  maintenance_window            = "sun:05:00-sun:06:00"

  log_delivery_configuration {
    destination_type = "cloudwatch-logs"
    destination      = aws_cloudwatch_log_group.redis_logs.name
    log_format       = "json"
  }
}

resource "aws_cloudwatch_log_group" "redis_logs" {
  name              = "/elasticache/${var.project_name}/redis"
  retention_in_days = 14
}
