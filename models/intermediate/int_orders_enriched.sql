with order_items as (

    select *
    from {{ ref('stg_order_items') }}

),

products as (

    select *
    from {{ ref('stg_products') }}

),

users as (

    select *
    from {{ ref('stg_users') }}

),

purchase_events as (

    select
        user_id,
        sequence_number,
        event_created_at,
        traffic_source
    from {{ ref('stg_events') }}
    where user_id is not null
      and event_type = 'purchase'

),

order_attribution as (

    select
        order_item_id,
        attributed_traffic_source
    from (
        select
            oi.order_item_id,
            pe.traffic_source as attributed_traffic_source,
            row_number() over (
                partition by oi.order_item_id
                order by
                    case when pe.event_created_at <= oi.order_item_created_at then 0 else 1 end,
                    abs(timestamp_diff(oi.order_item_created_at, pe.event_created_at, second)),
                    pe.event_created_at desc,
                    pe.sequence_number desc
            ) as rn
        from order_items oi
        left join purchase_events pe
            on oi.user_id = pe.user_id
           and pe.event_created_at between timestamp_sub(oi.order_item_created_at, interval 1 hour)
                                      and timestamp_add(oi.order_item_created_at, interval 1 hour)
    )
    where rn = 1

),

final as (

    select
        oi.order_item_id,
        oi.order_id,
        oi.user_id,
        oi.product_id,
        oi.inventory_item_id,
        oi.order_item_status,
        oi.order_item_created_at,
        oi.order_item_shipped_at,
        oi.order_item_delivered_at,
        oi.order_item_returned_at,
        oi.sale_price,

        p.product_name,
        p.category,
        p.brand,
        p.department,
        p.cost,
        p.retail_price,

        u.age,
        u.gender,
        u.country,
        coalesce(oa.attributed_traffic_source, u.signup_traffic_source, 'unknown') as traffic_source

    from order_items oi
    left join products p
        on oi.product_id = p.product_id
    left join users u
        on oi.user_id = u.user_id
    left join order_attribution oa
        on oi.order_item_id = oa.order_item_id

)

select *
from final
