import { Link } from 'react-router-dom';

export type BreadcrumbItem = {
  label: string;
  to?: string;
};

/**
 * Breadcrumb navigation component.
 * Renders a horizontal trail of links with a separator.
 *
 * Usage:
 *   <Breadcrumb items={[
 *     { label: 'Projects', to: '/projects' },
 *     { label: 'My Research', to: '/projects/abc/research' },
 *     { label: 'Extraction' },
 *   ]} />
 */
export function Breadcrumb({ items }: { items: BreadcrumbItem[] }) {
  if (items.length === 0) return null;
  return (
    <nav className="rc-breadcrumb" aria-label="Breadcrumb">
      {items.map((item, i) => {
        const isLast = i === items.length - 1;
        return (
          <span key={i} className="rc-breadcrumb__item">
            {i > 0 && <span className="rc-breadcrumb__sep" aria-hidden="true">/</span>}
            {item.to && !isLast ? (
              <Link to={item.to} className="rc-breadcrumb__link">{item.label}</Link>
            ) : (
              <span className={`rc-breadcrumb__current${isLast ? '' : ' rc-breadcrumb__link'}`}>{item.label}</span>
            )}
          </span>
        );
      })}
    </nav>
  );
}
