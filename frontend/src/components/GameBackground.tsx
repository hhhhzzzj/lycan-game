import { motion } from 'framer-motion';

interface Props {
    isNight: boolean;
}

export default function GameBackground({ isNight }: Props) {
    return (
        <div className="fixed inset-0 z-0 pointer-events-none">
            {/* Grain texture */}
            <div
                className="absolute inset-0"
                style={{
                    backgroundImage: `url("data:image/svg+xml,%3Csvg width='200' height='200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E")`,
                }}
            />

            {/* Night effects */}
            <motion.div
                className="absolute inset-0"
                initial={false}
                animate={{ opacity: isNight ? 1 : 0 }}
                transition={{ duration: 0.8 }}
            >
                {/* Moon */}
                <div
                    className="absolute top-[5%] right-[10%] w-[120px] h-[120px] rounded-full animate-float"
                    style={{
                        background: 'radial-gradient(circle, rgba(180,200,255,0.12) 0%, transparent 70%)',
                        filter: 'blur(2px)',
                    }}
                />
                {/* Blood fog */}
                <div
                    className="absolute inset-0 animate-fog"
                    style={{
                        background: `
              radial-gradient(ellipse at 20% 80%, rgba(107,26,26,0.08) 0%, transparent 50%),
              radial-gradient(ellipse at 80% 20%, rgba(40,40,80,0.06) 0%, transparent 50%)
            `,
                    }}
                />
                {/* Vignette */}
                <div
                    className="absolute inset-0"
                    style={{
                        background: 'radial-gradient(ellipse, transparent 20%, rgba(0,0,0,0.8) 100%)',
                    }}
                />
            </motion.div>

            {/* Day effects */}
            <motion.div
                className="absolute inset-0"
                initial={false}
                animate={{ opacity: isNight ? 0 : 1 }}
                transition={{ duration: 0.8 }}
            >
                {/* Warm glow */}
                <div
                    className="absolute inset-0"
                    style={{
                        background: `
              radial-gradient(ellipse at 50% 30%, rgba(201,168,76,0.08) 0%, transparent 60%),
              radial-gradient(ellipse at 30% 70%, rgba(180,140,60,0.04) 0%, transparent 50%)
            `,
                    }}
                />
                {/* Top light */}
                <div
                    className="absolute top-0 left-[20%] w-[60%] h-[40%]"
                    style={{
                        background: 'radial-gradient(ellipse, rgba(255,240,200,0.06) 0%, transparent 70%)',
                    }}
                />
                {/* Softer vignette */}
                <div
                    className="absolute inset-0"
                    style={{
                        background: 'radial-gradient(ellipse, transparent 40%, rgba(10,8,5,0.5) 100%)',
                    }}
                />
            </motion.div>
        </div>
    );
}
