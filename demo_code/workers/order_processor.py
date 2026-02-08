# workers/order_processor.py
def process_order(ch, method, props, body):
    try:
        order = json.loads(body)
        fulfill_order(order)
        # Only ACK after success
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        logger.error(f"Processing failed: {e}")