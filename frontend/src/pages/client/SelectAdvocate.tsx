import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { clientApi } from '../../services/api';
import {
  ArrowLeft,
  Star,
  MapPin,
  Briefcase,
  Languages,
  Clock,
  Check,
} from 'lucide-react';

interface Recommendation {
  advocate_id: string;
  name: string;
  email: string;
  phone: string;
  enrollment_number: string;
  match_score: number;
  match_reasons: string[];
  years_of_practice: number;
  home_court: string;
  specializations: string[];
  sub_specializations: string[];
  fee_category: string;
  consultation_fee: number | null;
  languages: string[];
  rating: number;
  review_count: number;
  office_address: string;
  is_verified: boolean;
  current_availability: string;
}

export default function SelectAdvocate() {
  const { id: caseId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [selecting, setSelecting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadRecommendations();
  }, [caseId]);

  const loadRecommendations = async () => {
    if (!caseId) return;
    try {
      const response = await clientApi.getRecommendations(caseId);
      setRecommendations(response.data.recommendations);
    } catch (err) {
      console.error('Failed to load recommendations:', err);
      setError('Failed to load advocate recommendations');
    } finally {
      setLoading(false);
    }
  };

  const selectAdvocate = async (advocateId: string) => {
    if (!caseId || selecting) return;
    setSelecting(advocateId);
    setError(null);

    try {
      await clientApi.selectAdvocate(caseId, advocateId);
      navigate('/client/cases', {
        state: { message: 'Request sent to advocate. You will be notified when they respond.' },
      });
    } catch (err) {
      console.error('Failed to select advocate:', err);
      setError('Failed to send request to advocate');
      setSelecting(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center">
          <button
            onClick={() => navigate(-1)}
            className="p-2 hover:bg-gray-100 rounded-full mr-4"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-xl font-semibold">Recommended Advocates</h1>
            <p className="text-sm text-gray-500">
              Select an advocate to handle your case
            </p>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        {recommendations.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg shadow-sm">
            <Briefcase className="h-16 w-16 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No advocates found matching your case criteria</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {recommendations.map((advocate, index) => (
              <div
                key={advocate.advocate_id}
                className="bg-white rounded-lg shadow-sm overflow-hidden"
              >
                {/* Match score header */}
                <div
                  className={`px-6 py-3 ${
                    index === 0
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">
                      {index === 0 ? 'Best Match' : `Match #${index + 1}`}
                    </span>
                    <span className="text-lg font-bold">{advocate.match_score}% Match</span>
                  </div>
                </div>

                {/* Advocate details */}
                <div className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                        {advocate.name}
                        {advocate.is_verified && (
                          <Check className="h-5 w-5 text-green-500 ml-2" />
                        )}
                      </h3>
                      <p className="text-sm text-gray-500">{advocate.enrollment_number}</p>
                    </div>
                    <div className="flex items-center">
                      <Star className="h-5 w-5 text-yellow-400 fill-current" />
                      <span className="ml-1 font-medium">{advocate.rating}</span>
                      <span className="text-sm text-gray-500 ml-1">
                        ({advocate.review_count})
                      </span>
                    </div>
                  </div>

                  {/* Match reasons */}
                  <div className="mb-4">
                    <div className="flex flex-wrap gap-2">
                      {advocate.match_reasons.slice(0, 3).map((reason, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-1 bg-green-50 text-green-700 text-xs rounded-full"
                        >
                          {reason}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Details grid */}
                  <div className="grid grid-cols-2 gap-4 text-sm mb-4">
                    <div className="flex items-center text-gray-600">
                      <Briefcase className="h-4 w-4 mr-2" />
                      {advocate.years_of_practice} years experience
                    </div>
                    <div className="flex items-center text-gray-600">
                      <MapPin className="h-4 w-4 mr-2" />
                      {advocate.home_court}
                    </div>
                    <div className="flex items-center text-gray-600">
                      <Languages className="h-4 w-4 mr-2" />
                      {advocate.languages.slice(0, 3).join(', ')}
                    </div>
                    <div className="flex items-center text-gray-600">
                      <Clock className="h-4 w-4 mr-2" />
                      {advocate.current_availability} availability
                    </div>
                  </div>

                  {/* Specializations */}
                  <div className="mb-4">
                    <p className="text-xs text-gray-500 mb-2">Specializations</p>
                    <div className="flex flex-wrap gap-2">
                      {advocate.specializations.map((spec, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded capitalize"
                        >
                          {spec}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Fee info */}
                  <div className="flex items-center justify-between pt-4 border-t">
                    <div>
                      <span className="text-sm text-gray-500">Consultation Fee:</span>
                      <span className="ml-2 font-semibold">
                        {advocate.consultation_fee
                          ? `₹${advocate.consultation_fee.toLocaleString()}`
                          : 'Contact for fee'}
                      </span>
                      <span className="ml-2 px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded capitalize">
                        {advocate.fee_category}
                      </span>
                    </div>
                  </div>

                  {/* Select button */}
                  <button
                    onClick={() => selectAdvocate(advocate.advocate_id)}
                    disabled={selecting !== null}
                    className={`w-full mt-4 py-3 px-4 rounded-lg font-medium transition-colors ${
                      selecting === advocate.advocate_id
                        ? 'bg-gray-200 text-gray-500 cursor-wait'
                        : 'bg-primary-600 text-white hover:bg-primary-700'
                    } disabled:opacity-50`}
                  >
                    {selecting === advocate.advocate_id
                      ? 'Sending Request...'
                      : 'Select This Advocate'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
